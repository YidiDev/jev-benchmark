"""Per-(student, question) prose specs: which of a question's rubric
criteria a student's answer should satisfy (determined by their true
score for that question), and the brief Sonnet must follow to write a
realistic paragraph-style answer embodying exactly that.

Which specific criteria are satisfied (not just how many) is chosen by a
seeded RNG per (student, question) -- not always the first N -- so a
partial-credit answer realistically covers a random subset of the
question's checkable elements, the way a real student might recall some
facts and forget or garble others, rather than always getting the
"first half" of the rubric right.
"""

from __future__ import annotations

from harness.constants import sub_rng
from examgrade.questions import ExamQuestion

STYLE_FLAVORS = ["organized", "rambling", "terse", "hedging"]
_STYLE_GUIDE = {
    "organized": "clearly organized, roughly one sentence or two per point being made",
    "rambling": "somewhat rambling and stream-of-consciousness, circling back and restating things",
    "terse": "very terse and minimal, short choppy sentences, not much elaboration",
    "hedging": "hedging and uncertain in tone ('I think...', 'I'm not totally sure but...'), even when the content is correct",
}


def assign_style(student_id: str, question_id: str) -> str:
    rng = sub_rng(f"examgrade_style::{student_id}::{question_id}")
    return rng.choice(STYLE_FLAVORS)


def select_satisfied_criteria(question: ExamQuestion, true_score: int, student_id: str) -> list[int]:
    """0-based indices of which of the question's criteria the student's
    answer should satisfy, given their true score for this question."""
    rng = sub_rng(f"examgrade_criteria_subset::{student_id}::{question.id}")
    indices = list(range(question.points))
    rng.shuffle(indices)
    return sorted(indices[:true_score])


def build_answer_brief(question: ExamQuestion, true_score: int, student_id: str) -> dict:
    satisfied = select_satisfied_criteria(question, true_score, student_id)
    unsatisfied = [i for i in range(question.points) if i not in satisfied]
    style = assign_style(student_id, question.id)

    satisfied_facts = [question.reference_facts[i] for i in satisfied]
    missing_criteria = [question.criteria[i] for i in unsatisfied]

    if true_score == question.points:
        instruction = (
            f"Write a complete, accurate paragraph answer that correctly covers ALL of the "
            f"following facts: {satisfied_facts}. This should read as a strong, fully correct answer."
        )
    elif true_score == 0:
        instruction = (
            "Write a paragraph answer that is confidently WRONG or entirely off-topic/vague -- it "
            "should not correctly address any of the substantive elements a correct answer would "
            "need. It should still look like a genuine attempt (not a blank or 'I don't know'), just "
            "incorrect, confused, or too generic to earn credit on any specific point."
        )
    else:
        instruction = (
            f"Write a partial-credit paragraph answer. It should correctly and clearly cover ONLY "
            f"these specific facts: {satisfied_facts}. It must NOT address or correctly convey these "
            f"other elements (omit them entirely, or address them vaguely/incorrectly so they clearly "
            f"do not earn credit): {missing_criteria}. Do not explicitly flag which parts you left out "
            "-- just write a natural, incomplete student answer."
        )

    return {
        "question_id": question.id,
        "prompt": question.prompt,
        "true_score": true_score,
        "max_points": question.points,
        "style": style,
        "style_guide": _STYLE_GUIDE[style],
        "instruction": instruction,
    }
