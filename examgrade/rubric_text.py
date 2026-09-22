"""Builds the grading-instructions text handed to a model for one exam
question, in both the with-answer-key and without-answer-key conditions.

The with/without split is the core of CT10's design (methodology.md §15):
`criteria` describes structurally what earns a point, never the actual
correct content; `reference_facts` (the actual correct content) is only
appended when `with_key=True`. Without the key, a grading model must rely
on its own historical knowledge to judge whether a criterion is factually
satisfied -- there is nothing in the rubric text itself that leaks the
answer.
"""

from __future__ import annotations

from examgrade.questions import EXAM_QUESTIONS, ExamQuestion


def question_rubric_text(question: ExamQuestion, with_key: bool) -> str:
    lines = [
        f'Question ({question.id}, worth {question.points} points): "{question.prompt}"',
        f"Award one point for each of the following {question.points} criteria the answer satisfies:",
    ]
    for i, criterion in enumerate(question.criteria, 1):
        line = f"  {i}. {criterion}"
        if with_key:
            line += f" [Correct content: {question.reference_facts[i - 1]}]"
        lines.append(line)
    if not with_key:
        lines.append(
            "No answer key is provided for this question -- use your own knowledge of AP World "
            "History to judge whether each criterion is factually and specifically satisfied, not "
            "just plausible-sounding."
        )
    lines.append(f"Score = the number of criteria satisfied, from 0 to {question.points}.")
    return "\n".join(lines)


def score_level_descriptions(points: int) -> list[str]:
    """Ordered level descriptions for Jev/OpenJev's Score primitive, index i
    = "i of `points` criteria satisfied"."""
    return [f"{i} of {points} criteria satisfied" for i in range(points + 1)]


def full_exam_rubric_text(with_key: bool) -> str:
    """All 30 questions' rubrics concatenated -- used for whole-exam-mode
    grading, where a single call must grade every question at once."""
    return "\n\n".join(question_rubric_text(q, with_key) for q in EXAM_QUESTIONS)
