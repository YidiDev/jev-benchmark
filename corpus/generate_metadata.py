"""Stage A of corpus generation: structured metadata only, zero API cost.

Produces `corpus/manifest.jsonl`, stratified across each clause type's
folders and split into validation/test. This is the sole ground-truth
source (rubrics/ground_truth.py) and is generated *before* any document
prose exists, satisfying the independence control in methodology.md §2.

Run: `python -m corpus.generate_metadata`
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from harness.constants import (
    TEST_DOCS_PER_CLAUSE,
    VALIDATION_DOCS_PER_CLAUSE,
    sub_rng,
)
from corpus.schema import DocumentMetadata
from rubrics.clause_specs import (
    CT2_THRESHOLD_USD,
    CT3_FIXTURES,
    CT5_THRESHOLD_USD,
    CT7_FIXTURES,
    CT7_FOLDERS,
)

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


def _split_into_parts(total: float, n: int, rng) -> list[float]:
    """Split `total` into `n` positive parts that sum to exactly `total`
    (to the cent) -- used so CT5's line items always add up precisely,
    even though the document never states the total itself."""
    if n == 1:
        return [round(total, 2)]
    cuts = sorted(rng.uniform(0, total) for _ in range(n - 1))
    bounds = [0.0, *cuts, total]
    parts = [round(b - a, 2) for a, b in zip(bounds, bounds[1:])]
    # Rounding can drift the sum by a cent or two; correct it on the last part.
    drift = round(total - sum(parts), 2)
    parts[-1] = round(parts[-1] + drift, 2)
    # Extremely unlikely with reasonable totals/n, but guard against a
    # rounding-driven non-positive part.
    if any(p <= 0 for p in parts):
        return _split_into_parts(total, n, rng)
    return parts


def _gen_ct5(n: int, split: str, rng) -> list[DocumentMetadata]:
    # Mirrors CT2's large/small + hard/easy structure, but the target value
    # is a *sum of line items* the document lists individually, never a
    # stated total -- see rubrics/clause_specs.py's CT5 docstring.
    counts = _stratified_counts(n, 2)  # [over_count, under_count]
    rows = []
    idx = 0
    for bucket, count in zip(("over", "under"), counts):
        n_hard = round(count * 0.3)
        n_easy = count - n_hard
        for is_hard in [True] * n_hard + [False] * n_easy:
            idx += 1
            if bucket == "over":
                total = (
                    rng.uniform(CT5_THRESHOLD_USD + 1, CT5_THRESHOLD_USD + 300)
                    if is_hard
                    else rng.uniform(CT5_THRESHOLD_USD + 300, CT5_THRESHOLD_USD + 20_000)
                )
            else:
                total = (
                    rng.uniform(CT5_THRESHOLD_USD - 300, CT5_THRESHOLD_USD)
                    if is_hard
                    else rng.uniform(50, CT5_THRESHOLD_USD - 300)
                )
            n_items = rng.randint(2, 5)
            line_items = _split_into_parts(round(total, 2), n_items, rng)
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct5_{split[:2]}_{idx:03d}",
                    clause_type=5,
                    split=split,
                    line_items=line_items,
                    seed_trace={
                        "purpose": f"ct5_metadata::{split}",
                        "bucket": bucket,
                        "hard": is_hard,
                        "total": round(sum(line_items), 2),
                    },
                )
            )
    rng.shuffle(rows)
    return rows


def _random_date(rng, start_year: int = 2022, end_year: int = 2025) -> date:
    year = rng.randint(start_year, end_year)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)  # sidesteps month-length edge cases
    return date(year, month, day)


def _gen_ct6(n: int, split: str, rng) -> list[DocumentMetadata]:
    # 50/50 current/prior, ~30% "hard" (dates close together, small gap) vs
    # ~70% "easy" (dates far apart) -- mirrors CT2/CT5's hard/easy split.
    counts = _stratified_counts(n, 2)  # [current_count, prior_count]
    rows = []
    idx = 0
    for bucket, count in zip(("current", "prior"), counts):
        n_hard = round(count * 0.3)
        n_easy = count - n_hard
        for is_hard in [True] * n_hard + [False] * n_easy:
            idx += 1
            reference = _random_date(rng)
            delta_days = rng.randint(1, 30) if is_hard else rng.randint(60, 720)
            if bucket == "current":
                effective = reference + timedelta(days=delta_days)
            else:
                effective = reference - timedelta(days=delta_days)
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct6_{split[:2]}_{idx:03d}",
                    clause_type=6,
                    split=split,
                    effective_date=effective.isoformat(),
                    reference_date=reference.isoformat(),
                    seed_trace={
                        "purpose": f"ct6_metadata::{split}",
                        "bucket": bucket,
                        "hard": is_hard,
                        "delta_days": delta_days,
                    },
                )
            )
    rng.shuffle(rows)
    return rows


def _gen_ct7(n: int, split: str, rng) -> list[DocumentMetadata]:
    # Stratified across the 3 program folders. The document only ever names
    # a *team* -- the model must chain team->division->program via the
    # rubric's two tables (rubrics/clause_specs.py's CT7 docstring).
    program_to_teams: dict[str, list[str]] = defaultdict(list)
    for team, division in CT7_FIXTURES.team_to_division.items():
        program = CT7_FIXTURES.division_to_program[division]
        program_to_teams[program].append(team)

    counts = _stratified_counts(n, len(CT7_FOLDERS))
    rows = []
    idx = 0
    for program, count in zip(CT7_FOLDERS, counts):
        teams_for_program = program_to_teams[program]
        for _ in range(count):
            idx += 1
            team = rng.choice(teams_for_program)
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct7_{split[:2]}_{idx:03d}",
                    clause_type=7,
                    split=split,
                    team=team,
                    seed_trace={"purpose": f"ct7_metadata::{split}", "bucket": program},
                )
            )
    rng.shuffle(rows)
    return rows


def _gen_ct8(n: int, split: str, rng) -> list[DocumentMetadata]:
    # Same stratified structure as CT1, distinct doc_type value set -- the
    # difficulty here is entirely in the prose (corpus/prose_prompts.py
    # pads these documents with irrelevant boilerplate), not the metadata.
    doc_types = ["tax_form", "invoice_doc", "contract_doc"]
    counts = _stratified_counts(n, len(doc_types))
    rows = []
    idx = 0
    for doc_type, count in zip(doc_types, counts):
        for _ in range(count):
            idx += 1
            rows.append(
                DocumentMetadata(
                    doc_id=f"ct8_{split[:2]}_{idx:03d}",
                    clause_type=8,
                    split=split,
                    doc_type=doc_type,
                    seed_trace={"purpose": f"ct8_metadata::{split}", "bucket": doc_type},
                )
            )
    rng.shuffle(rows)
    return rows


_GENERATORS = {
    1: _gen_ct1,
    2: _gen_ct2,
    3: _gen_ct3,
    4: _gen_ct4,
    5: _gen_ct5,
    6: _gen_ct6,
    7: _gen_ct7,
    8: _gen_ct8,
}


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
