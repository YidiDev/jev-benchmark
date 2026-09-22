"""Scoring for CT10 exam grading: per-question grading error (MAE,
exact-match rate), per-student total-score error, chained-vs-whole-exam
comparison, and the with-key-vs-without-key comparison that separates
"can the model apply a rubric" from "does the model know world history."
"""

from __future__ import annotations

from collections import defaultdict

from harness.bootstrap import bootstrap_ci
from examgrade.predictions import GradeRecord, load_grades

ARMS = ("jev", "haiku", "openjev")
MODES = ("chained", "whole_exam")


def question_level_error(arm: str) -> list[dict]:
    """Per (mode, with_key): mean absolute error and exact-match rate at
    the individual-question level, across all 100 students x 30 questions."""
    records = load_grades(arm)
    buckets: dict[tuple[str, bool], list[GradeRecord]] = defaultdict(list)
    for r in records:
        buckets[(r.mode, r.with_key)].append(r)

    rows = []
    for (mode, with_key), recs in sorted(buckets.items()):
        errors = [abs(r.graded_score - r.true_score) for r in recs]
        exact = [r.graded_score == r.true_score for r in recs]
        n = len(recs)
        mae = sum(errors) / n
        exact_rate = sum(exact) / n
        lo, hi = bootstrap_ci(exact, purpose=f"examgrade_bootstrap::{arm}::{mode}::{with_key}")
        rows.append(
            {
                "arm": arm,
                "mode": mode,
                "with_key": with_key,
                "n": n,
                "mae": mae,
                "exact_match_rate": exact_rate,
                "exact_match_ci_lo": lo,
                "exact_match_ci_hi": hi,
            }
        )
    return rows


def total_score_error(arm: str) -> list[dict]:
    """Per (mode, with_key): mean absolute error between a student's
    graded total (summed from 30 per-question scores) and their true
    total, out of 100 -- across all 100 students."""
    records = load_grades(arm)
    buckets: dict[tuple[str, bool], dict[str, list[GradeRecord]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        buckets[(r.mode, r.with_key)][r.student_id].append(r)

    rows = []
    for (mode, with_key), by_student in sorted(buckets.items()):
        errors = []
        for student_id, recs in by_student.items():
            graded_total = sum(r.graded_score for r in recs)
            true_total = sum(r.true_score for r in recs)
            errors.append(abs(graded_total - true_total))
        n = len(errors)
        mae = sum(errors) / n
        rows.append({"arm": arm, "mode": mode, "with_key": with_key, "n_students": n, "total_score_mae": mae})
    return rows


def with_vs_without_key_delta(arm: str) -> list[dict]:
    """Per mode: exact-match rate with the answer key minus without --
    the "does the model actually know world history" signal. A small
    delta means the model's own knowledge is nearly as good as being
    handed the answer; a large delta means it leans heavily on the key."""
    rows = question_level_error(arm)
    by_key = {(r["mode"], r["with_key"]): r for r in rows}
    out = []
    for mode in MODES:
        with_row = by_key.get((mode, True))
        without_row = by_key.get((mode, False))
        if with_row and without_row:
            out.append(
                {
                    "arm": arm,
                    "mode": mode,
                    "exact_match_with_key": with_row["exact_match_rate"],
                    "exact_match_without_key": without_row["exact_match_rate"],
                    "delta": with_row["exact_match_rate"] - without_row["exact_match_rate"],
                }
            )
    return out


def chained_vs_whole_exam_delta(arm: str) -> list[dict]:
    """Per with_key condition: chained exact-match rate minus whole-exam
    -- does isolated per-question context help or hurt vs. grading
    everything in one shared-context call?"""
    rows = question_level_error(arm)
    by_key = {(r["mode"], r["with_key"]): r for r in rows}
    out = []
    for with_key in (True, False):
        chained_row = by_key.get(("chained", with_key))
        whole_row = by_key.get(("whole_exam", with_key))
        if chained_row and whole_row:
            out.append(
                {
                    "arm": arm,
                    "with_key": with_key,
                    "exact_match_chained": chained_row["exact_match_rate"],
                    "exact_match_whole_exam": whole_row["exact_match_rate"],
                    "delta": chained_row["exact_match_rate"] - whole_row["exact_match_rate"],
                }
            )
    return out


def confidence_at_errors(arm: str, mode: str = "chained") -> dict:
    """Only meaningful for arms/modes that report confidence -- Jev and
    OpenJev report confidence in both modes; Haiku only reports it in
    chained mode (its whole-exam tool schema has no per-question
    confidence field, since a single shared JSON object per exam
    isn't well suited to 30 separate confidence values)."""
    records = [r for r in load_grades(arm) if r.mode == mode and r.confidence is not None]
    errs = [r.confidence for r in records if r.graded_score != r.true_score]
    corr = [r.confidence for r in records if r.graded_score == r.true_score]

    def stats(xs: list[float]) -> dict | None:
        if not xs:
            return None
        return {"n": len(xs), "mean": sum(xs) / len(xs)}

    return {"arm": arm, "mode": mode, "at_errors": stats(errs), "at_correct": stats(corr)}


def cost_latency_table() -> list[dict]:
    out = []
    for arm in ARMS:
        records = load_grades(arm)
        if not records:
            continue
        n = len(records)
        avg_latency_ms = sum(r.latency_ms for r in records) / n
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        out.append(
            {
                "arm": arm,
                "n_grades": n,
                "avg_latency_ms": avg_latency_ms,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
            }
        )
    return out
