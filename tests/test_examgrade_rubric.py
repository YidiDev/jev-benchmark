from examgrade.questions import EXAM_BY_ID
from examgrade.rubric_text import (
    full_exam_rubric_text,
    question_rubric_text,
    score_level_descriptions,
)


def test_score_level_descriptions_length():
    for points in (2, 3, 4, 5):
        levels = score_level_descriptions(points)
        assert len(levels) == points + 1


def test_with_key_includes_reference_facts():
    q = EXAM_BY_ID["q07"]
    text = question_rubric_text(q, with_key=True)
    for fact in q.reference_facts:
        assert fact in text


def test_without_key_excludes_reference_facts():
    q = EXAM_BY_ID["q07"]
    text = question_rubric_text(q, with_key=False)
    for fact in q.reference_facts:
        assert fact not in text


def test_without_key_includes_all_criteria():
    q = EXAM_BY_ID["q13"]
    text = question_rubric_text(q, with_key=False)
    for criterion in q.criteria:
        assert criterion in text


def test_full_exam_rubric_text_covers_every_question():
    text = full_exam_rubric_text(with_key=True)
    from examgrade.questions import EXAM_QUESTIONS

    for q in EXAM_QUESTIONS:
        assert q.id in text
        assert q.prompt in text


def test_full_exam_rubric_without_key_never_leaks_any_fact():
    text = full_exam_rubric_text(with_key=False)
    from examgrade.questions import EXAM_QUESTIONS

    for q in EXAM_QUESTIONS:
        for fact in q.reference_facts:
            assert fact not in text
