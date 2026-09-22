from examgrade.prose_prompts import build_answer_brief, select_satisfied_criteria
from examgrade.questions import EXAM_BY_ID


def test_select_satisfied_criteria_correct_count():
    q = EXAM_BY_ID["q13"]  # 5 points
    for score in range(q.points + 1):
        satisfied = select_satisfied_criteria(q, score, "student_test")
        assert len(satisfied) == score
        assert all(0 <= i < q.points for i in satisfied)


def test_select_satisfied_criteria_reproducible():
    q = EXAM_BY_ID["q13"]
    a = select_satisfied_criteria(q, 3, "student_test")
    b = select_satisfied_criteria(q, 3, "student_test")
    assert a == b


def test_build_answer_brief_full_score_mentions_all_facts():
    q = EXAM_BY_ID["q05"]  # 2 points
    brief = build_answer_brief(q, q.points, "student_test")
    for fact in q.reference_facts:
        assert fact in brief["instruction"]


def test_build_answer_brief_zero_score_is_confidently_wrong():
    q = EXAM_BY_ID["q05"]
    brief = build_answer_brief(q, 0, "student_test")
    assert "WRONG" in brief["instruction"] or "off-topic" in brief["instruction"]


def test_build_answer_brief_partial_score_excludes_missing_criteria_facts():
    q = EXAM_BY_ID["q13"]  # 5 points, so partial scores exist
    brief = build_answer_brief(q, 2, "student_test")
    satisfied = select_satisfied_criteria(q, 2, "student_test")
    unsatisfied_facts = [q.reference_facts[i] for i in range(q.points) if i not in satisfied]
    # unsatisfied facts should never appear in the instruction at all -- only
    # satisfied_facts are surfaced; missing ones are referenced via their
    # structural criteria text, never their reference_facts content.
    for fact in unsatisfied_facts:
        assert fact not in brief["instruction"]
