"""Orchestrates CT10 grading: for each student x question x with/without-
key condition, grades in both chained (one call per question) and
whole-exam (one call for all 30) modes. repeats=1 throughout (see
methodology.md §15's scope decisions).

Resumable: chained mode resumes per (student, question, with_key);
whole-exam mode resumes per (student, with_key) since one call produces
all 30 rows atomically.

Usage:
    python -m examgrade.runner --arm jev
    python -m examgrade.runner --arm haiku --limit 2 --modes chained  # debug
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from harness.spend_ledger import BudgetExceeded
from examgrade.generate_metadata import load_manifest
from examgrade.predictions import (
    GradeRecord,
    append_grade,
    existing_chained_keys,
    existing_whole_exam_students,
)
from examgrade.questions import EXAM_BY_ID, EXAM_QUESTIONS

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
KEY_CONDITIONS = (True, False)  # with_key, without_key
MODES = ("chained", "whole_exam")


def _student_text(student_id: str) -> str:
    return (DOCUMENTS_DIR / f"{student_id}.txt").read_text()


def _answer_text(full_text: str, question_id: str) -> str:
    """Extracts one question's answer text out of a student's full exam
    document -- used for chained mode, which grades one answer at a time."""
    marker = f"({question_id}, "
    start = full_text.index(marker)
    a_start = full_text.index("A: ", start) + len("A: ")
    next_q = full_text.find("\nQ (", a_start)
    end = next_q if next_q != -1 else len(full_text)
    return full_text[a_start:end].strip()


def _build_arm(name: str):
    if name == "jev":
        from examgrade.arms import JevExamArm

        return JevExamArm()
    if name == "haiku":
        from examgrade.arms import HaikuExamArm

        return HaikuExamArm()
    if name == "openjev":
        from examgrade.arms import OpenJevExamArm

        return OpenJevExamArm()
    raise ValueError(f"unknown CT10 arm {name!r}")


def run(
    arm_name: str,
    limit: int | None = None,
    modes: tuple[str, ...] = MODES,
    key_conditions: tuple[bool, ...] = KEY_CONDITIONS,
) -> None:
    print(f"[examgrade/{arm_name}] initializing (modes={modes}, keys={key_conditions})...")
    arm = _build_arm(arm_name)

    students = load_manifest()
    if limit:
        students = students[:limit]

    chained_done = existing_chained_keys(arm_name)
    whole_exam_done = existing_whole_exam_students(arm_name)

    n_seen = 0
    n_written = 0
    t0 = time.time()

    try:
        for student in students:
            full_text = _student_text(student.student_id)

            if "chained" in modes:
                for with_key in key_conditions:
                    for q in EXAM_QUESTIONS:
                        n_seen += 1
                        key = (student.student_id, q.id, with_key)
                        if key in chained_done:
                            continue
                        answer_text = _answer_text(full_text, q.id)
                        result = arm.grade_question(answer_text, q, with_key)
                        grade = result.grades[q.id]
                        append_grade(
                            GradeRecord(
                                arm=arm_name,
                                student_id=student.student_id,
                                question_id=q.id,
                                mode="chained",
                                with_key=with_key,
                                true_score=student.scores[q.id],
                                graded_score=grade.score,
                                max_points=q.points,
                                confidence=grade.confidence,
                                latency_ms=result.latency_ms,
                                input_tokens=result.input_tokens,
                                output_tokens=result.output_tokens,
                            )
                        )
                        n_written += 1
                        if n_seen % 100 == 0:
                            elapsed = time.time() - t0
                            print(f"[examgrade/{arm_name}] {n_seen} seen, {n_written} newly written ({elapsed:.1f}s elapsed)")

            if "whole_exam" in modes:
                for with_key in key_conditions:
                    n_seen += 1
                    key = (student.student_id, with_key)
                    if key in whole_exam_done:
                        continue
                    result = arm.grade_exam(full_text, with_key)
                    per_call_latency = result.latency_ms / len(EXAM_QUESTIONS)
                    per_call_input = result.input_tokens / len(EXAM_QUESTIONS)
                    per_call_output = result.output_tokens / len(EXAM_QUESTIONS)
                    for q in EXAM_QUESTIONS:
                        grade = result.grades[q.id]
                        append_grade(
                            GradeRecord(
                                arm=arm_name,
                                student_id=student.student_id,
                                question_id=q.id,
                                mode="whole_exam",
                                with_key=with_key,
                                true_score=student.scores[q.id],
                                graded_score=grade.score,
                                max_points=q.points,
                                confidence=grade.confidence,
                                latency_ms=per_call_latency,
                                input_tokens=round(per_call_input),
                                output_tokens=round(per_call_output),
                            )
                        )
                    n_written += 1
                    if n_seen % 20 == 0:
                        elapsed = time.time() - t0
                        print(f"[examgrade/{arm_name}] {n_seen} seen, {n_written} newly written ({elapsed:.1f}s elapsed)")
    except BudgetExceeded as e:
        print(f"[examgrade/{arm_name}] STOPPED (budget): {e}")
        raise
    finally:
        if hasattr(arm, "close"):
            arm.close()

    elapsed = time.time() - t0
    print(f"[examgrade/{arm_name}] done: {n_seen} seen, {n_written} newly written in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=["jev", "haiku", "openjev"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--modes", nargs="+", choices=["chained", "whole_exam"], default=None)
    args = parser.parse_args()
    modes = tuple(args.modes) if args.modes else MODES
    run(args.arm, limit=args.limit, modes=modes)
