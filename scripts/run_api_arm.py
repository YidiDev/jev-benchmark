"""Generic runner for stochastic, token-metered API arms (jev, haiku,
openjev): executes `repeats` passes over the full corpus manifest under all
three folder-naming conditions PLUS the shuffle control, and writes
results/predictions/{arm}.jsonl.

Unlike scripts/run_arm.py (local deterministic arms, repeat=1 only), this
runner loops REPEATS=3 times per (doc_id, condition) since these arms are
stochastic even at temperature 0 -- test-plan.md's run-to-run variance
requirement explicitly covers Haiku at temp 0 for this reason.

**Condition "SHUFFLE" IS run separately here, unlike scripts/run_arm.py.**
This is a deliberate difference, not an oversight: these arms are handed
the full rubric text (`rubric.instructions`/`rubric.criteria`), and that
text is genuinely different between Condition B and SHUFFLE --
`rubrics.clauses.build_rubric(ct, "SHUFFLE")` formats the same rule template
with a *permuted* canonical-id -> display-name mapping, so the literal
sentences sent to the model differ (e.g. "Tax documents go to `w1tqk1`" in B
vs "Tax documents go to `fh4pr2`" under SHUFFLE for the same clause type).
An earlier version of this harness reused Condition B's predictions for the
shuffle control here too (valid for nli-bart/emb-bge, which only ever see
the folder-id *set*, never the rubric text, so B and SHUFFLE present an
identical classification problem to them) -- but for rubric-reading arms
that is wrong: it silently never asked the model to follow the shuffled
rubric at all, so scoring B's answers against the shuffled key just measures
"did the model coincidentally guess the derangement," which is ~0% by
construction whenever the model is in fact reading the rubric (a derangement
has zero fixed points, so 100% B-accuracy under the true mapping guarantees
~0% under any relabeling once you evaluate the *same* answers against it).
See methodology.md §8 for the full writeup of this fix.

Resumable and budget-aware: every predict() call for a paid arm logs through
harness.spend_ledger.record_spend from inside the arm implementation itself.
A BudgetExceeded exception propagates up and stops the run immediately
(already-written predictions are preserved; rerun to resume once the budget
situation is resolved).

Usage:
    python -m scripts.run_api_arm --arm jev
    python -m scripts.run_api_arm --arm jev --limit 5 --repeats 1   # debug
    python -m scripts.run_api_arm --arm jev --split validation      # pilot
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from corpus.generate_metadata import load_manifest
from harness.constants import CONDITIONS, REPEATS
from harness.predictions import PredictionRecord, append_prediction, existing_keys
from harness.spend_ledger import BudgetExceeded
from rubrics.clauses import build_rubric

# Rubric-reading API arms need a real run under the shuffled rubric text, on
# top of the three folder-naming conditions -- see module docstring.
API_ARM_CONDITIONS = (*CONDITIONS, "SHUFFLE")

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "documents"


def _doc_text(doc_id: str) -> str:
    return (DOCUMENTS_DIR / f"{doc_id}.txt").read_text()


def _build_arm(name: str):
    if name == "jev":
        from arms.jev import JevArm

        return JevArm()
    if name == "haiku":
        from arms.haiku import HaikuArm

        return HaikuArm()
    if name == "openjev":
        from arms.openjev import OpenJevArm

        return OpenJevArm()
    raise ValueError(f"unknown API arm {name!r} (nli-bart/emb-bge use scripts.run_arm)")


def run(
    arm_name: str,
    limit: int | None = None,
    repeats: int | None = None,
    split: str | None = None,
) -> None:
    repeats = repeats or REPEATS
    print(f"[{arm_name}] initializing client (repeats={repeats})...")
    arm = _build_arm(arm_name)

    manifest = load_manifest()
    if split:
        manifest = [m for m in manifest if m.split == split]
    if limit:
        manifest = manifest[:limit]
    done = existing_keys(arm_name)

    total = len(manifest) * len(API_ARM_CONDITIONS) * repeats
    n_seen = 0
    n_written = 0
    t0 = time.time()

    try:
        for metadata in manifest:
            text = _doc_text(metadata.doc_id)
            for condition in API_ARM_CONDITIONS:
                rubric = build_rubric(metadata.clause_type, condition)
                for repeat in range(1, repeats + 1):
                    n_seen += 1
                    key = (metadata.doc_id, condition, repeat)
                    if key in done:
                        continue
                    pred = arm.predict(text, rubric)
                    record = PredictionRecord(
                        arm=arm_name,
                        doc_id=metadata.doc_id,
                        clause_type=metadata.clause_type,
                        condition=condition,
                        split=metadata.split,
                        repeat=repeat,
                        predicted_folder=pred.folder,
                        probabilities=pred.probabilities,
                        confidence=pred.confidence,
                        latency_ms=pred.latency_ms,
                        input_tokens=pred.input_tokens,
                        output_tokens=pred.output_tokens,
                    )
                    append_prediction(record)
                    n_written += 1
                    if n_seen % 25 == 0:
                        elapsed = time.time() - t0
                        print(
                            f"[{arm_name}] {n_seen}/{total} seen, {n_written} newly written "
                            f"({elapsed:.1f}s elapsed)"
                        )
    except BudgetExceeded as e:
        print(f"[{arm_name}] STOPPED (budget): {e}")
        raise
    finally:
        if hasattr(arm, "close"):
            arm.close()

    elapsed = time.time() - t0
    print(f"[{arm_name}] done: {n_seen}/{total} seen, {n_written} newly written in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=["jev", "haiku", "openjev"])
    parser.add_argument("--limit", type=int, default=None, help="limit to first N manifest rows (debug)")
    parser.add_argument("--repeats", type=int, default=None, help="override REPEATS (debug)")
    parser.add_argument("--split", choices=["validation", "test"], default=None, help="restrict to one split")
    args = parser.parse_args()
    run(args.arm, limit=args.limit, repeats=args.repeats, split=args.split)
