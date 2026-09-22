"""Consolidates every computed metric across every test (CT1-8, CT9, and
CT10 once built) into one machine-readable artifact for later analysis,
so nobody has to re-derive numbers from raw predictions or re-read prose
tables out of methodology.md/results.md.

Outputs:
  results/summary.json -- full nested structure (everything full_report()
    and qtree.scoring's functions produce, plus spend), keyed by section.
  results/summary.csv  -- flattened long-format rows (one row per
    arm/metric/breakdown-key), easy to pivot in a spreadsheet or pandas.

Aggregated metrics only -- raw per-prediction data already lives in
results/predictions/*.jsonl and is not duplicated here. Re-run any time
new data lands (OpenJev, CT10): `python -m scripts.generate_summary`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from harness.predictions import load_predictions as load_ct1_8_predictions
from harness.scoring import ALL_KNOWN_ARMS as CT1_8_ARMS
from harness.scoring import full_report as ct1_8_full_report
from harness.spend_ledger import cumulative_spend, summarize as spend_summarize
from qtree.predictions import load_chunks as load_ct9_chunks
from qtree.scoring import ARMS as CT9_ARMS
from qtree.scoring import (
    all_local_correct_rate,
    confidence_at_local_errors,
    disagreement_at_k10,
    end_to_end_accuracy,
    local_step_accuracy,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
JSON_PATH = RESULTS_DIR / "summary.json"
CSV_PATH = RESULTS_DIR / "summary.csv"


def _ct9_report() -> dict:
    arms_present = [a for a in CT9_ARMS if load_ct9_chunks(a)]
    return {
        "arms": arms_present,
        "end_to_end_accuracy": {a: end_to_end_accuracy(a) for a in arms_present},
        "local_step_accuracy": {a: local_step_accuracy(a) for a in arms_present},
        "all_local_correct_rate": {a: all_local_correct_rate(a) for a in arms_present},
        "confidence_at_local_errors": {a: confidence_at_local_errors(a) for a in arms_present},
        "disagreement_at_k10": {
            a: {lbl: disagreement_at_k10(a, lbl) for lbl in ("semantic", "opaque")} for a in arms_present
        },
    }


def _spend_report() -> dict:
    return {
        "by_source_model": spend_summarize(),
        "anthropic_cumulative_usd": cumulative_spend("anthropic"),
    }


def build_summary() -> dict:
    summary = {
        "ct1_8": ct1_8_full_report() if any(load_ct1_8_predictions(a) for a in CT1_8_ARMS) else None,
        "ct9": _ct9_report() if any(load_ct9_chunks(a) for a in CT9_ARMS) else None,
        "ct10": None,  # populated once examgrade/ exists and has data
        "spend": _spend_report(),
    }
    return summary


def _flatten_ct1_8(rows: list[dict], report: dict) -> None:
    if report is None:
        return
    for arm, accuracy_rows in report["accuracy"].items():
        for r in accuracy_rows:
            rows.append(
                {
                    "section": "ct1_8",
                    "arm": arm,
                    "metric": "accuracy",
                    "clause_type": r["clause_type"],
                    "condition": r["condition"],
                    "k": None,
                    "labeling": None,
                    "value": r["accuracy"],
                    "n": r["n"],
                    "extra": f"ci=[{r['ci_lo']:.4f},{r['ci_hi']:.4f}]",
                }
            )
    for arm, oa in report["overall_accuracy"].items():
        rows.append(
            {
                "section": "ct1_8", "arm": arm, "metric": "overall_accuracy", "clause_type": None,
                "condition": None, "k": None, "labeling": None, "value": oa["accuracy"], "n": oa["n"],
                "extra": f"ci=[{oa['ci_lo']:.4f},{oa['ci_hi']:.4f}]",
            }
        )
    for arm, deltas in report["shuffle_delta"].items():
        for d in deltas:
            rows.append(
                {
                    "section": "ct1_8", "arm": arm, "metric": "shuffle_delta", "clause_type": d["clause_type"],
                    "condition": None, "k": None, "labeling": None, "value": d["delta"], "n": None,
                    "extra": f"b={d['b_accuracy']:.4f} shuffle={d['shuffle_accuracy']:.4f}",
                }
            )
    for arm, calib in report["calibration"].items():
        rows.append(
            {
                "section": "ct1_8", "arm": arm, "metric": "raw_ece", "clause_type": None, "condition": None,
                "k": None, "labeling": None, "value": calib["raw_ece"], "n": calib["n_test"], "extra": "",
            }
        )
        rows.append(
            {
                "section": "ct1_8", "arm": arm, "metric": "fitted_ece", "clause_type": None, "condition": None,
                "k": None, "labeling": None, "value": calib["fitted_ece"], "n": calib["n_test"],
                "extra": f"T={calib['fitted_temperature']:.2f}",
            }
        )
    for arm, ce in report["confidence_at_errors"].items():
        if ce["at_errors"]:
            rows.append(
                {
                    "section": "ct1_8", "arm": arm, "metric": "confidence_at_errors", "clause_type": None,
                    "condition": None, "k": None, "labeling": None, "value": ce["at_errors"]["mean"],
                    "n": ce["at_errors"]["n"], "extra": "",
                }
            )
        if ce["at_correct"]:
            rows.append(
                {
                    "section": "ct1_8", "arm": arm, "metric": "confidence_at_correct", "clause_type": None,
                    "condition": None, "k": None, "labeling": None, "value": ce["at_correct"]["mean"],
                    "n": ce["at_correct"]["n"], "extra": "",
                }
            )
    for arm, dis in report["disagreement"].items():
        rows.append(
            {
                "section": "ct1_8", "arm": arm, "metric": "disagreement_rate", "clause_type": None,
                "condition": None, "k": None, "labeling": None, "value": dis["rate"],
                "n": dis["total_groups"], "extra": "",
            }
        )
    for row in report["cost_latency"]:
        rows.append(
            {
                "section": "ct1_8", "arm": row["arm"], "metric": "avg_latency_ms", "clause_type": None,
                "condition": None, "k": None, "labeling": None, "value": row["avg_latency_ms"],
                "n": row["n_predictions"], "extra": "",
            }
        )
        rows.append(
            {
                "section": "ct1_8", "arm": row["arm"], "metric": "total_cost_usd", "clause_type": None,
                "condition": None, "k": None, "labeling": None, "value": row["total_cost_usd"],
                "n": row["n_predictions"], "extra": f"per_doc=${row['cost_per_doc_usd']:.6f}",
            }
        )


def _flatten_ct9(rows: list[dict], report: dict) -> None:
    if report is None:
        return
    for arm, accuracy_rows in report["end_to_end_accuracy"].items():
        for r in accuracy_rows:
            rows.append(
                {
                    "section": "ct9", "arm": arm, "metric": "end_to_end_accuracy", "clause_type": None,
                    "condition": None, "k": r["k"], "labeling": r["labeling"], "value": r["accuracy"],
                    "n": r["n"], "extra": f"ci=[{r['ci_lo']:.4f},{r['ci_hi']:.4f}]",
                }
            )
    for arm, local_rows in report["local_step_accuracy"].items():
        for r in local_rows:
            rows.append(
                {
                    "section": "ct9", "arm": arm, "metric": "local_step_accuracy", "clause_type": None,
                    "condition": None, "k": r["k"], "labeling": None, "value": r["accuracy"], "n": r["n"],
                    "extra": f"ci=[{r['ci_lo']:.4f},{r['ci_hi']:.4f}]",
                }
            )
    for arm, conf in report["confidence_at_local_errors"].items():
        if conf["at_local_errors"]:
            rows.append(
                {
                    "section": "ct9", "arm": arm, "metric": "confidence_at_local_errors", "clause_type": None,
                    "condition": None, "k": None, "labeling": None, "value": conf["at_local_errors"]["mean"],
                    "n": conf["at_local_errors"]["n"], "extra": "",
                }
            )
        if conf["at_local_correct"]:
            rows.append(
                {
                    "section": "ct9", "arm": arm, "metric": "confidence_at_local_correct", "clause_type": None,
                    "condition": None, "k": None, "labeling": None, "value": conf["at_local_correct"]["mean"],
                    "n": conf["at_local_correct"]["n"], "extra": "",
                }
            )
    for arm, by_labeling in report["disagreement_at_k10"].items():
        for labeling, dis in by_labeling.items():
            rows.append(
                {
                    "section": "ct9", "arm": arm, "metric": "disagreement_at_k10", "clause_type": None,
                    "condition": None, "k": 10, "labeling": labeling, "value": dis["rate"],
                    "n": dis["total_forms"], "extra": "",
                }
            )


def _flatten_spend(rows: list[dict], spend: dict) -> None:
    for key, agg in spend["by_source_model"].items():
        rows.append(
            {
                "section": "spend", "arm": agg["source"], "metric": "cost_usd", "clause_type": None,
                "condition": None, "k": None, "labeling": None, "value": agg["cost_usd"], "n": agg["calls"],
                "extra": f"model={agg['model']}",
            }
        )
    rows.append(
        {
            "section": "spend", "arm": "TOTAL", "metric": "anthropic_cumulative_usd", "clause_type": None,
            "condition": None, "k": None, "labeling": None, "value": spend["anthropic_cumulative_usd"],
            "n": None, "extra": "",
        }
    )


def flatten(summary: dict) -> list[dict]:
    rows: list[dict] = []
    _flatten_ct1_8(rows, summary["ct1_8"])
    _flatten_ct9(rows, summary["ct9"])
    _flatten_spend(rows, summary["spend"])
    return rows


def write_json(summary: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {JSON_PATH}")


def write_csv(rows: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["section", "arm", "metric", "clause_type", "condition", "k", "labeling", "value", "n", "extra"]
    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {CSV_PATH} ({len(rows)} rows)")


if __name__ == "__main__":
    summary = build_summary()
    write_json(summary)
    write_csv(flatten(summary))
