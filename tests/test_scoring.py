"""Integration tests for harness/scoring.py against the real, committed
results/predictions/*.jsonl data -- there's no separate small fixture
corpus, so these tests validate structural invariants and known-true facts
about the actual benchmark run rather than constructing synthetic data.
"""

from harness.constants import CLAUSE_TYPES
from harness.scoring import (
    ALL_KNOWN_ARMS,
    accuracy_table,
    calibration_report,
    confidence_at_errors,
    cost_latency_table,
    disagreement,
    effective_records,
    overall_accuracy,
    shuffle_delta_table,
)


def test_accuracy_table_covers_every_clause_type_and_condition():
    rows = accuracy_table("jev")
    seen = {(r.clause_type, r.condition) for r in rows}
    for ct in CLAUSE_TYPES:
        for cond in ("A", "B", "C", "SHUFFLE"):
            assert (ct, cond) in seen, f"missing ({ct}, {cond})"


def test_accuracy_table_n_matches_expected_prediction_count():
    # 60 docs (50 test + 10 validation) per clause type x 3 repeats = 180
    rows = accuracy_table("jev")
    for r in rows:
        assert r.n == 180


def test_jev_ct1_4_is_perfect():
    rows = accuracy_table("jev")
    for r in rows:
        if r.clause_type in (1, 2, 3, 4):
            assert r.accuracy == 1.0
            assert r.ci_lo == 1.0
            assert r.ci_hi == 1.0


def test_local_arms_shuffle_is_synthesized_from_condition_b():
    # nli-bart/emb-bge never see rubric text, so their SHUFFLE predictions
    # (synthesized) must have identical predicted_folder values to their
    # real Condition B predictions, doc-for-doc.
    b_preds = {r.doc_id: r.predicted_folder for r in effective_records("nli-bart") if r.condition == "B"}
    shuffle_preds = {
        r.doc_id: r.predicted_folder for r in effective_records("nli-bart") if r.condition == "SHUFFLE"
    }
    assert b_preds == shuffle_preds
    assert len(b_preds) > 0


def test_api_arms_have_real_shuffle_predictions_not_synthesized():
    # jev/haiku see rubric text, so real SHUFFLE calls were made -- this
    # doesn't prove non-synthesis directly, but combined with
    # test_shuffle_rubric_text_differs_from_condition_b (tests/test_run_api_arm.py)
    # and the 100% jev accuracy under an adversarial permutation, confirms
    # real (not reused) predictions were made.
    rows = [r for r in accuracy_table("jev") if r.condition == "SHUFFLE"]
    assert len(rows) == len(CLAUSE_TYPES)
    for r in rows:
        assert r.n == 180


def test_overall_accuracy_structure():
    for arm in ("jev", "haiku", "sonnet"):
        result = overall_accuracy(arm)
        assert result["arm"] == arm
        assert result["n"] > 0
        assert 0.0 <= result["accuracy"] <= 1.0
        assert result["ci_lo"] <= result["accuracy"] <= result["ci_hi"]


def test_shuffle_delta_near_zero_for_jev():
    # Jev tracks the permuted rubric perfectly (§10/§12) -- B and SHUFFLE
    # accuracy should be identical (both 1.0) for CT1-4.
    deltas = shuffle_delta_table("jev")
    for d in deltas:
        if d["clause_type"] in (1, 2, 3, 4):
            assert d["delta"] == 0.0


def test_confidence_at_errors_jev_ct5_lower_than_at_correct():
    # The headline calibration finding from methodology.md §12 Finding 4 --
    # regression-tested so it can't silently regress.
    stats = confidence_at_errors("jev")
    assert stats["at_errors"] is not None
    assert stats["at_correct"] is not None
    assert stats["at_errors"]["mean"] < stats["at_correct"]["mean"]


def test_calibration_report_structure():
    for arm in ("jev", "haiku", "sonnet"):
        report = calibration_report(arm)
        assert report["n_validation"] > 0
        assert report["n_test"] > 0
        assert 0.0 <= report["raw_ece"] <= 1.0
        assert 0.0 <= report["fitted_ece"] <= 1.0


def test_disagreement_bounds():
    for arm in ("jev", "haiku", "sonnet", "nli-bart", "emb-bge"):
        result = disagreement(arm)
        assert 0.0 <= result["rate"] <= 1.0
        assert result["disagreeing_groups"] <= result["total_groups"]


def test_local_arms_never_disagree_with_themselves():
    # Deterministic, repeat=1 only -- there's only ever one prediction per
    # (doc_id, condition) group, so disagreement is structurally impossible.
    for arm in ("nli-bart", "emb-bge"):
        result = disagreement(arm)
        assert result["disagreeing_groups"] == 0


def test_cost_latency_table_has_an_entry_per_arm_with_predictions():
    table = cost_latency_table()
    arms_present = {row["arm"] for row in table}
    for arm in arms_present:
        assert arm in ALL_KNOWN_ARMS
    for row in table:
        assert row["n_predictions"] > 0
        assert row["avg_latency_ms"] >= 0
        assert row["total_cost_usd"] >= 0
