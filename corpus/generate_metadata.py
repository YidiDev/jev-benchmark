"""Stage A of corpus generation: structured metadata only, zero API cost.

Produces `corpus/manifest.jsonl`, stratified across each clause type's
folders and split into validation/test. This is the sole ground-truth
source (rubrics/ground_truth.py) and is generated *before* any document
prose exists, satisfying the independence control in methodology.md §2.

Run: `python -m corpus.generate_metadata`
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.constants import (
    TEST_DOCS_PER_CLAUSE,
    VALIDATION_DOCS_PER_CLAUSE,
    sub_rng,
)
from corpus.schema import DocumentMetadata
from rubrics.clause_specs import CT2_THRESHOLD_USD, CT3_FIXTURES

MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.jsonl"


def _stratified_counts(n: int, k: int) -> list[int]:
    """Split n items into k buckets as evenly as possible."""
    base, remainder = divmod(n, k)
    return [base + (1 if i < remainder else 0) for i in range(k)]


def _gen_ct1(n: int, split: str, rng) -> list[DocumentMetadata]:
    doc_types = ["tax", "invoices", "contracts"]
    counts = _stratified_counts(n, len(doc_types))
    rows = []
    idx = 0
    for doc_type, count in zip(doc_types, counts):
        for _ in range(count):
            idx += 1
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct1_{split[:2]}_{idx:03d}",
                    clause_type=1,
                    split=split,
                    doc_type=doc_type,
                    seed_trace={"purpose": f"ct1_metadata::{split}", "bucket": doc_type},
                )
            )
    rng.shuffle(rows)
    return rows


def _gen_ct2(n: int, split: str, rng) -> list[DocumentMetadata]:
    # Half large, half small; within each half, ~30% "hard" (near threshold),
    # rest "easy" (clearly above/below). Stratified across the large/small
    # split, not hand-tuned per document.
    counts = _stratified_counts(n, 2)  # [large_count, small_count]
    rows = []
    idx = 0
    for bucket, count in zip(("large", "small"), counts):
        n_hard = round(count * 0.3)
        n_easy = count - n_hard
        for is_hard in [True] * n_hard + [False] * n_easy:
            idx += 1
            if bucket == "large":
                amount = (
                    rng.uniform(CT2_THRESHOLD_USD + 1, CT2_THRESHOLD_USD + 2_000)
                    if is_hard
                    else rng.uniform(CT2_THRESHOLD_USD + 2_000, 250_000)
                )
            else:
                amount = (
                    rng.uniform(CT2_THRESHOLD_USD - 2_000, CT2_THRESHOLD_USD)
                    if is_hard
                    else rng.uniform(50, CT2_THRESHOLD_USD - 2_000)
                )
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct2_{split[:2]}_{idx:03d}",
                    clause_type=2,
                    split=split,
                    amount_usd=round(amount, 2),
                    seed_trace={
                        "purpose": f"ct2_metadata::{split}",
                        "bucket": bucket,
                        "hard": is_hard,
                    },
                )
            )
    rng.shuffle(rows)
    return rows


def _gen_ct3(n: int, split: str, rng) -> list[DocumentMetadata]:
    codename_a, codename_b = CT3_FIXTURES.project_codenames
    retainer_list = sorted(CT3_FIXTURES.retainer_clients)
    non_retainer = [c for c in CT3_FIXTURES.all_client_candidates if c not in CT3_FIXTURES.retainer_clients]

    buckets = ["project_one", "project_two", "retainer_clients"]
    counts = _stratified_counts(n, len(buckets))
    rows = []
    idx = 0
    for bucket, count in zip(buckets, counts):
        for _ in range(count):
            idx += 1
            if bucket == "retainer_clients":
                project = rng.choice([codename_a, codename_b])  # distractor project affiliation
                client = rng.choice(retainer_list)
            else:
                project = codename_a if bucket == "project_one" else codename_b
                # ~50% chance of a non-retainer client mentioned as a distractor,
                # so "any client name present" is never a valid shortcut.
                client = rng.choice(non_retainer) if rng.random() < 0.5 else None
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct3_{split[:2]}_{idx:03d}",
                    clause_type=3,
                    split=split,
                    project_codename=project,
                    mentioned_client=client,
                    seed_trace={"purpose": f"ct3_metadata::{split}", "bucket": bucket},
                )
            )
    rng.shuffle(rows)
    return rows


def _gen_ct4(n: int, split: str, rng) -> list[DocumentMetadata]:
    counts = _stratified_counts(n, 2)  # [active_count, superseded_count]
    rows = []
    idx = 0
    for is_superseded, count in zip((False, True), counts):
        for _ in range(count):
            idx += 1
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct4_{split[:2]}_{idx:03d}",
                    clause_type=4,
                    split=split,
                    is_superseded=is_superseded,
                    seed_trace={
                        "purpose": f"ct4_metadata::{split}",
                        "bucket": "superseded" if is_superseded else "active",
                    },
                )
            )
    rng.shuffle(rows)
    return rows


_GENERATORS = {1: _gen_ct1, 2: _gen_ct2, 3: _gen_ct3, 4: _gen_ct4}


def generate_all() -> list[DocumentMetadata]:
    rows: list[DocumentMetadata] = []
    for ct, gen_fn in _GENERATORS.items():
        for split, n in (("test", TEST_DOCS_PER_CLAUSE), ("validation", VALIDATION_DOCS_PER_CLAUSE)):
            rng = sub_rng(f"corpus::ct{ct}::{split}")
            rows.extend(gen_fn(n, split, rng))
    return rows


def write_manifest(rows: list[DocumentMetadata]) -> None:
    with MANIFEST_PATH.open("w") as f:
        for row in rows:
            f.write(row.model_dump_json() + "\n")


def load_manifest() -> list[DocumentMetadata]:
    rows = []
    with MANIFEST_PATH.open() as f:
        for line in f:
            if line.strip():
                rows.append(DocumentMetadata(**json.loads(line)))
    return rows


if __name__ == "__main__":
    rows = generate_all()
    write_manifest(rows)
    by_ct_split: dict[tuple[int, str], int] = {}
    for r in rows:
        key = (r.clause_type, r.split)
        by_ct_split[key] = by_ct_split.get(key, 0) + 1
    print(f"Wrote {len(rows)} metadata rows to {MANIFEST_PATH}")
    for (ct, split), count in sorted(by_ct_split.items()):
        print(f"  ct{ct} {split}: {count}")
