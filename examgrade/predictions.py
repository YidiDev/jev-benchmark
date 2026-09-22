"""Grading-result storage for CT10. One row per (arm, student, question,
mode, with_key) -- in whole-exam mode, one API call produces all 30 rows
for a given (student, with_key); in chained mode, one call produces
exactly one row. repeats=1 throughout (per the reduced-scope decision),
so there's no repeat dimension here unlike harness/predictions.py and
qtree/predictions.py.

One JSONL file per arm at results/predictions/examgrade_{arm}.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PREDICTIONS_DIR = Path(__file__).resolve().parent.parent / "results" / "predictions"


@dataclass
class GradeRecord:
    arm: str
    student_id: str
    question_id: str
    mode: str  # "chained" | "whole_exam"
    with_key: bool
    true_score: int
    graded_score: int
    max_points: int
    confidence: float | None
    latency_ms: float
    input_tokens: int
    output_tokens: int


def path_for(arm: str) -> Path:
    return PREDICTIONS_DIR / f"examgrade_{arm}.jsonl"


def append_grade(record: GradeRecord) -> None:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    with path_for(record.arm).open("a") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def load_grades(arm: str) -> list[GradeRecord]:
    p = path_for(arm)
    if not p.exists():
        return []
    rows = []
    with p.open() as f:
        for line in f:
            if line.strip():
                rows.append(GradeRecord(**json.loads(line)))
    return rows


def existing_chained_keys(arm: str) -> set[tuple[str, str, bool]]:
    """(student_id, question_id, with_key) already graded in chained mode."""
    return {
        (r.student_id, r.question_id, r.with_key) for r in load_grades(arm) if r.mode == "chained"
    }


def existing_whole_exam_students(arm: str) -> set[tuple[str, bool]]:
    """(student_id, with_key) pairs that already have all 30 whole-exam rows."""
    from examgrade.questions import EXAM_QUESTIONS

    n_questions = len(EXAM_QUESTIONS)
    counts: dict[tuple[str, bool], int] = {}
    for r in load_grades(arm):
        if r.mode == "whole_exam":
            key = (r.student_id, r.with_key)
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count >= n_questions}
