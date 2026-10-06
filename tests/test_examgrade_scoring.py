from examgrade.predictions import GradeRecord, existing_chained_keys, existing_whole_exam_students
from examgrade.scoring import (
    chained_vs_whole_exam_delta,
    confidence_at_errors,
    cost_latency_table,
    question_level_error,
    total_score_error,
    with_vs_without_key_delta,
)


# Arms with both chained and whole-exam data (Nimble is chained-only -- its
# whole-exam mode is documented unsupported, see examgrade/arms.py's
# NimbleExamArm -- so it's tested separately below, not in this set).
FULL_MODE_ARMS = ("jev", "haiku", "sonnet", "openjev", "kev", "laya", "cygnet", "winnow", "strands")


def test_question_level_error_structure():
    for arm in FULL_MODE_ARMS:
        rows = question_level_error(arm)
        assert len(rows) == 4  # 2 modes x 2 key conditions
        for r in rows:
            assert 0.0 <= r["exact_match_rate"] <= 1.0
            assert r["mae"] >= 0.0
            assert r["n"] == 3000  # 100 students x 30 questions


def test_total_score_error_structure():
    for arm in FULL_MODE_ARMS:
        rows = total_score_error(arm)
        assert len(rows) == 4
        for r in rows:
            assert r["n_students"] == 100
            assert r["total_score_mae"] >= 0.0


def test_with_vs_without_key_delta_structure():
    for arm in FULL_MODE_ARMS:
        rows = with_vs_without_key_delta(arm)
        assert len(rows) == 2  # chained, whole_exam
        for r in rows:
            assert abs(r["delta"] - (r["exact_match_with_key"] - r["exact_match_without_key"])) < 1e-9


def test_chained_vs_whole_exam_delta_structure():
    for arm in FULL_MODE_ARMS:
        rows = chained_vs_whole_exam_delta(arm)
        assert len(rows) == 2  # with_key True/False
        for r in rows:
            assert abs(r["delta"] - (r["exact_match_chained"] - r["exact_match_whole_exam"])) < 1e-9


def test_nimble_chained_only_structure():
    # Whole-exam mode is documented unsupported for Nimble (examgrade/arms.py's
    # NimbleExamArm.grade_exam raises NotImplementedError) -- only chained-mode
    # data exists on disk, so these functions should see exactly that shape.
    rows = question_level_error("nimble")
    assert len(rows) == 2  # chained x with_key True/False only
    for r in rows:
        assert r["mode"] == "chained"
        assert r["n"] == 3000
        assert 0.0 <= r["exact_match_rate"] <= 1.0

    rows = total_score_error("nimble")
    assert len(rows) == 2
    for r in rows:
        assert r["mode"] == "chained"
        assert r["n_students"] == 100

    # No whole_exam row to pair with -- chained_vs_whole_exam_delta finds no
    # (mode, with_key) pair for either with_key value and returns nothing.
    assert chained_vs_whole_exam_delta("nimble") == []


def test_jev_confidence_discriminates_errors_from_correct():
    conf = confidence_at_errors("jev", mode="chained")
    assert conf["at_errors"]["mean"] < conf["at_correct"]["mean"]


def test_cost_latency_table_has_all_arms():
    table = cost_latency_table()
    arms = {row["arm"] for row in table}
    assert arms == set(FULL_MODE_ARMS) | {"nimble"}
    by_arm = {row["arm"]: row for row in table}
    for arm in FULL_MODE_ARMS:
        assert by_arm[arm]["n_grades"] == 12000
    assert by_arm["nimble"]["n_grades"] == 6000  # chained only, no whole_exam rows


def test_existing_chained_keys_predictions_module():
    keys = existing_chained_keys("jev")
    assert len(keys) == 100 * 30 * 2  # students x questions x key-conditions


def test_existing_whole_exam_students_predictions_module():
    students = existing_whole_exam_students("jev")
    assert len(students) == 100 * 2  # students x key-conditions
