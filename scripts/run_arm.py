"""Generic runner for the local baseline arms: executes one arm across the
full corpus manifest (every document, splits validation+test) under all
three folder-naming conditions and writes results/predictions/{arm}.jsonl.

Condition "SHUFFLE" is deliberately never run separately here: the shuffle
control (test-plan.md §5.1) presents the model with the exact same
opaque-id folder set as Condition B, so re-running would be identical work
for identical output -- only the scoring-time answer key differs. See
harness/predictions.py and (later) harness/scoring.py.

Local arms (nli-bart, emb-bge) are deterministic (no sampling), so each
(doc_id, condition) pair is run once (repeat=1) -- repeating a deterministic
forward pass produces byte-identical output and adds no statistical signal.
Stochastic API arms (jev, haiku, openjev) get their own runners using
REPEATS=3 from harness/constants.py.

Resumable: skips any (doc_id, condition, repeat=1) already present in the
output file, so an interrupted run can restart cheaply.

Usage:
    python -m scripts.run_arm --arm nli-bart
    python -m scripts.run_arm --arm emb-bge
    python -m scripts.run_arm --arm nli-bart --limit 5   # debug: first 5 manifest rows
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from corpus.generate_metadata import load_manifest
from harness.constants import CONDITIONS
from harness.predictions import PredictionRecord, append_prediction, existing_keys
from rubrics.clauses import build_rubric

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "documents"


def _doc_text(doc_id: str) -> str:
    return (DOCUMENTS_DIR / f"{doc_id}.txt").read_text()


def _build_arm(name: str):
    if name == "nli-bart":
        from arms.nli_bart import NliBartArm

        return NliBartArm()
    if name == "emb-bge":
        from arms.emb_bge import EmbBgeArm

        return EmbBgeArm()
    raise ValueError(f"unknown local arm {name!r} (Jev/Haiku/OpenJev have dedicated runners)")


def run(arm_name: str, limit: int | None = None) -> None:
    print(f"[{arm_name}] loading model...")
    arm = _build_arm(arm_name)

    manifest = load_manifest()
    if limit:
        manifest = manifest[:limit]
    done = existing_keys(arm_name)

    total = len(manifest) * len(CONDITIONS)
    n_seen = 0
    n_written = 0
    t0 = time.time()

    for metadata in manifest:
        text = _doc_text(metadata.doc_id)
        for condition in CONDITIONS:
            n_seen += 1
            key = (metadata.doc_id, condition, 1)
            if key in done:
                continue
            rubric = build_rubric(metadata.clause_type, condition)
            pred = arm.predict(text, rubric)
            record = PredictionRecord(
                arm=arm_name,
                doc_id=metadata.doc_id,
                clause_type=metadata.clause_type,
                condition=condition,
                split=metadata.split,
                repeat=1,
                predicted_folder=pred.folder,
                probabilities=pred.probabilities,
                confidence=pred.confidence,
                latency_ms=pred.latency_ms,
                input_tokens=pred.input_tokens,
                output_tokens=pred.output_tokens,
            )
            append_prediction(record)
            n_written += 1
            if n_seen % 50 == 0:
                elapsed = time.time() - t0
                print(f"[{arm_name}] {n_seen}/{total} seen, {n_written} newly written ({elapsed:.1f}s elapsed)")

    elapsed = time.time() - t0
    print(f"[{arm_name}] done: {n_seen}/{total} seen, {n_written} newly written in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=["nli-bart", "emb-bge"])
    parser.add_argument("--limit", type=int, default=None, help="limit to first N manifest rows (debug)")
    args = parser.parse_args()
    run(args.arm, limit=args.limit)
