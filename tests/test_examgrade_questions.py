from examgrade.questions import EXAM_BY_ID, EXAM_QUESTIONS, TOTAL_POINTS


def test_thirty_questions_summing_to_100():
    assert len(EXAM_QUESTIONS) == 30
    assert TOTAL_POINTS == 100


def test_every_question_criteria_and_facts_match_points():
    for q in EXAM_QUESTIONS:
        assert len(q.criteria) == q.points
        assert len(q.reference_facts) == q.points


def test_non_uniform_point_distribution():
    points = {q.points for q in EXAM_QUESTIONS}
    assert len(points) > 1  # not all questions worth the same


def test_exam_by_id_covers_all_questions():
    assert set(EXAM_BY_ID.keys()) == {q.id for q in EXAM_QUESTIONS}


# The precise, non-heuristic leakage guarantee (criteria text handed to a
# without-key grading call never contains any reference_fact verbatim) is
# tested directly in tests/test_examgrade_rubric.py against the actual
# rubric text an arm receives -- that's the guarantee that matters. A
# naive substring heuristic here on generic connective phrases (e.g. "this
# challenged...") produced false positives and added no real coverage.
