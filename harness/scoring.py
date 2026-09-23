"""Scoring harness: turns raw results/predictions/{arm}.jsonl files into the
metrics test-plan.md §6 asks for -- accuracy per (condition x clause type)
with bootstrap 95% CI, shuffle-control delta, calibration ECE (raw +
temperature-fit), confidence-at-errors, run-to-run disagreement, and
cost/latency. This is the single source of truth results.md's tables are
built from; nothing in results.md should be a number that didn't come
through this module (or its `python -m harness.scoring` report).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace

from corpus.generate_metadata import load_manifest
from corpus.schema import DocumentMetadata
from harness.bootstrap import bootstrap_ci
from harness.calibration import apply_temperature, ece, fit_temperature
from harness.constants import CLAUSE_TYPES
from harness.predictions import PredictionRecord, load_predictions
from harness.spend_ledger import summarize as summarize_spend
from rubrics.ground_truth import correct_folder

# nli-bart/emb-bge never see rubric text -- only the folder-id set, which is
# identical between Condition B and SHUFFLE -- so their Condition B
# predictions are reused as-is for SHUFFLE scoring (see scripts/run_arm.py's
# docstring). jev/haiku/openjev DO see rubric text that differs between B
# and SHUFFLE, so they have real SHUFFLE records on disk already.
ARMS_SYNTHESIZE_SHUFFLE_FROM_B = {"nli-bart", "emb-bge"}

# Arms whose `confidence` is a genuine per-call estimate worth calibrating.
# nli-bart/emb-bge's confidence-like scores are documented as uncalibrated
# in their own modules (temperature-1 softmax over raw scores) and excluded.
CALIBRATION_ARMS = {"jev", "haiku", "openjev", "sonnet"}

ALL_KNOWN_ARMS = ("jev", "haiku", "nli-bart", "emb-bge", "openjev", "sonnet")


def _manifest_index() -> dict[str, DocumentMetadata]:
    return {m.doc_id: m for m in load_manifest()}


def _truth_for(record: PredictionRecord, metadata: DocumentMetadata) -> str:
    if record.condition == "SHUFFLE":
        return correct_folder(metadata, shuffle=True)
    return correct_folder(metadata, condition=record.condition)


def effective_records(arm: str) -> list[PredictionRecord]:
    """All predictions for `arm`, covering A/B/C/SHUFFLE uniformly --
    synthesizing SHUFFLE from Condition B for arms that never see rubric
    text (see module docstring)."""
    records = load_predictions(arm)
    if arm in ARMS_SYNTHESIZE_SHUFFLE_FROM_B:
        records = records + [replace(r, condition="SHUFFLE") for r in records if r.condition == "B"]
    return records


@dataclass
class AccuracyRow:
    arm: str
    clause_type: int
    condition: str
    n: int
    correct: int
    accuracy: float
    ci_lo: float
    ci_hi: float


def accuracy_table(arm: str) -> list[AccuracyRow]:
    manifest = _manifest_index()
    records = effective_records(arm)
    buckets: dict[tuple[int, str], list[bool]] = defaultdict(list)
    for r in records:
        md = manifest[r.doc_id]
        truth = _truth_for(r, md)
        buckets[(r.clause_type, r.condition)].append(r.predicted_folder == truth)

    rows = []
    for (ct, cond), values in sorted(buckets.items()):
        n = len(values)
        correct = sum(values)
        acc = correct / n
        lo, hi = bootstrap_ci(values, purpose=f"bootstrap::{arm}::ct{ct}::{cond}")
        rows.append(AccuracyRow(arm, ct, cond, n, correct, acc, lo, hi))
    return rows


def overall_accuracy(arm: str) -> dict:
    records = effective_records(arm)
    manifest = _manifest_index()
    values = [r.predicted_folder == _truth_for(r, manifest[r.doc_id]) for r in records]
    n = len(values)
    correct = sum(values)
    lo, hi = bootstrap_ci(values, purpose=f"bootstrap::{arm}::overall")
    return {"arm": arm, "n": n, "correct": correct, "accuracy": correct / n if n else 0.0, "ci_lo": lo, "ci_hi": hi}


def shuffle_delta_table(arm: str) -> list[dict]:
    """Per clause_type: Condition-B accuracy minus SHUFFLE accuracy. Near 0
    means genuine rubric-conditioning (tracks a permuted mapping just as
    well as the true one, per test-plan.md §5.1); a large positive delta
    means reliance on content priors (collapses once the mapping is
    adversarially permuted)."""
    rows = accuracy_table(arm)
    by_key = {(r.clause_type, r.condition): r for r in rows}
    out = []
    for ct in CLAUSE_TYPES:
        b = by_key.get((ct, "B"))
        s = by_key.get((ct, "SHUFFLE"))
        if b is not None and s is not None:
            out.append(
                {
                    "arm": arm,
                    "clause_type": ct,
                    "b_accuracy": b.accuracy,
                    "shuffle_accuracy": s.accuracy,
                    "delta": b.accuracy - s.accuracy,
                }
            )
    return out


def confidence_at_errors(arm: str) -> dict:
    """Mean/min/max confidence among misclassified vs. correct predictions."""
    manifest = _manifest_index()
    records = effective_records(arm)
    error_conf, correct_conf = [], []
    for r in records:
        if r.confidence is None:
            continue
        truth = _truth_for(r, manifest[r.doc_id])
        (correct_conf if r.predicted_folder == truth else error_conf).append(r.confidence)

    def stats(xs: list[float]) -> dict | None:
        if not xs:
            return None
        return {"n": len(xs), "mean": sum(xs) / len(xs), "min": min(xs), "max": max(xs)}

    return {"arm": arm, "at_errors": stats(error_conf), "at_correct": stats(correct_conf)}


def calibration_report(arm: str) -> dict:
    """Raw ECE (computed on the test split) + a single temperature fit on
    the validation split, applied to the test split -- per test-plan.md §6.
    Only meaningful for arms with a genuine confidence estimate."""
    manifest = _manifest_index()
    records = effective_records(arm)
    val_pairs, test_pairs = [], []
    for r in records:
        if r.confidence is None:
            continue
        md = manifest[r.doc_id]
        truth = _truth_for(r, md)
        pair = (r.confidence, r.predicted_folder == truth)
        (val_pairs if md.split == "validation" else test_pairs).append(pair)

    raw_ece_test = ece(test_pairs)
    temperature = fit_temperature(val_pairs) if val_pairs else 1.0
    fitted_pairs = [(apply_temperature(c, temperature), correct) for c, correct in test_pairs]
    fitted_ece_test = ece(fitted_pairs)

    return {
        "arm": arm,
        "n_validation": len(val_pairs),
        "n_test": len(test_pairs),
        "raw_ece": raw_ece_test,
        "fitted_temperature": temperature,
        "fitted_ece": fitted_ece_test,
    }


def disagreement(arm: str) -> dict:
    """Fraction of (doc_id, condition) groups where not every repeat agreed
    on the predicted folder -- run-to-run variance, per test-plan.md §6."""
    records = effective_records(arm)
    by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in records:
        by_key[(r.doc_id, r.condition)].add(r.predicted_folder)
    total = len(by_key)
    disagreeing = sum(1 for preds in by_key.values() if len(preds) > 1)
    return {
        "arm": arm,
        "total_groups": total,
        "disagreeing_groups": disagreeing,
        "rate": disagreeing / total if total else 0.0,
    }


def cost_latency_table() -> list[dict]:
    """Actual logged latency + spend per arm -- real numbers, not list
    price, per test-plan.md's cost/latency requirement."""
    spend_by_source = summarize_spend()
    source_for_arm = {"jev": "jev_arm", "haiku": "haiku_arm", "openjev": "openjev_arm", "sonnet": "sonnet_arm"}

    out = []
    for arm in ALL_KNOWN_ARMS:
        records = load_predictions(arm)
        if not records:
            continue
        n = len(records)
        avg_latency_ms = sum(r.latency_ms for r in records) / n
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)

        cost_usd = 0.0
        source = source_for_arm.get(arm)
        if source:
            for key, agg in spend_by_source.items():
                if agg["source"] == source:
                    cost_usd += agg["cost_usd"]

        out.append(
            {
                "arm": arm,
                "n_predictions": n,
                "avg_latency_ms": avg_latency_ms,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_cost_usd": cost_usd,
                "cost_per_doc_usd": cost_usd / n if n else 0.0,
            }
        )
    return out


def full_report() -> dict:
    """Everything test-plan.md §6 asks for, for every arm that has any
    predictions on disk."""
    arms_present = [arm for arm in ALL_KNOWN_ARMS if load_predictions(arm)]
    return {
        "arms": arms_present,
        "accuracy": {arm: [row.__dict__ for row in accuracy_table(arm)] for arm in arms_present},
        "overall_accuracy": {arm: overall_accuracy(arm) for arm in arms_present},
        "shuffle_delta": {arm: shuffle_delta_table(arm) for arm in arms_present},
        "confidence_at_errors": {arm: confidence_at_errors(arm) for arm in arms_present},
        "calibration": {arm: calibration_report(arm) for arm in arms_present if arm in CALIBRATION_ARMS},
        "disagreement": {arm: disagreement(arm) for arm in arms_present},
        "cost_latency": cost_latency_table(),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(full_report(), indent=2))
