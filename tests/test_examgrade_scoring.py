from examgrade.predictions import GradeRecord, existing_chained_keys, existing_whole_exam_students
from examgrade.scoring import (
    chained_vs_whole_exam_delta,
    confidence_at_errors,
    cost_latency_table,
    question_level_error,
    total_score_error,
    with_vs_without_key_delta,
)


def test_question_level_error_structure():
    for arm in ("jev", "haiku", "sonnet", "openjev"):
        rows = question_level_error(arm)
        assert len(rows) == 4  # 2 modes x 2 key conditions
        for r in rows:
            assert 0.0 <= r["exact_match_rate"] <= 1.0
            assert r["mae"] >= 0.0
            assert r["n"] == 3000  # 100 students x 30 questions


def test_total_score_error_structure():
    for arm in ("jev", "haiku", "sonnet", "openjev"):
        rows = total_score_error(arm)
        assert len(rows) == 4
        for r in rows:
            assert r["n_students"] == 100
            assert r["total_score_mae"] >= 0.0


def test_with_vs_without_key_delta_structure():
    for arm in ("jev", "haiku", "sonnet", "openjev"):
        rows = with_vs_without_key_delta(arm)
        assert len(rows) == 2  # chained, whole_exam
        for r in rows:
            assert abs(r["delta"] - (r["exact_match_with_key"] - r["exact_match_without_key"])) < 1e-9


def test_chained_vs_whole_exam_delta_structure():
    for arm in ("jev", "haiku", "sonnet", "openjev"):
        rows = chained_vs_whole_exam_delta(arm)
        assert len(rows) == 2  # with_key True/False
        for r in rows:
            assert abs(r["delta"] - (r["exact_match_chained"] - r["exact_match_whole_exam"])) < 1e-9


def test_jev_confidence_discriminates_errors_from_correct():
    conf = confidence_at_errors("jev", mode="chained")
    assert conf["at_errors"]["mean"] < conf["at_correct"]["mean"]


def test_cost_latency_table_has_all_arms():
    table = cost_latency_table()
    arms = {row["arm"] for row in table}
    assert arms == {"jev", "haiku", "sonnet", "openjev"}
    for row in table:
        assert row["n_grades"] == 12000


def test_existing_chained_keys_predictions_module():
    keys = existing_chained_keys("jev")
    assert len(keys) == 100 * 30 * 2  # students x questions x key-conditions


def test_existing_whole_exam_students_predictions_module():
    students = existing_whole_exam_students("jev")
    assert len(students) == 100 * 2  # students x key-conditions
