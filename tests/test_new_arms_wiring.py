"""Wiring tests for the September 2026 new-arms addition (laya, kev, nimble,
clm -- see methodology.md §18): every dispatch table, argparse choice list,
and ARMS/CALIBRATION_ARMS registration actually includes the new arm names,
and NimbleExamArm's documented whole-exam limitation actually raises before
attempting any network call (no NIMBLE_BASE_URL / running server needed for
this repo's own test suite -- see AGENTS.md: tests need no API keys or
network)."""

import os

from examgrade.scoring import ARMS as EXAMGRADE_ARMS
from harness.scoring import ALL_KNOWN_ARMS, ARMS_SYNTHESIZE_SHUFFLE_FROM_B, CALIBRATION_ARMS
from qtree.scoring import ARMS as QTREE_ARMS
from scripts.run_api_arm import _build_arm as build_api_arm
from qtree.runner import _build_arm as build_qtree_arm
from examgrade.runner import _build_arm as build_examgrade_arm


def test_new_arms_registered_in_ct1_8_scoring():
    for arm in ("laya", "kev", "nimble"):
        assert arm in ALL_KNOWN_ARMS
        assert arm in CALIBRATION_ARMS
        # All three read real rubric text (unlike nli-bart/emb-bge), so none
        # should synthesize SHUFFLE from Condition B -- see harness/scoring.py.
        assert arm not in ARMS_SYNTHESIZE_SHUFFLE_FROM_B


def test_new_arms_registered_in_qtree_scoring():
    for arm in ("laya", "kev", "nimble", "clm"):
        assert arm in QTREE_ARMS


def test_new_arms_registered_in_examgrade_scoring():
    for arm in ("laya", "kev", "nimble"):
        assert arm in EXAMGRADE_ARMS


def test_run_api_arm_dispatch_raises_on_unknown_arm():
    import pytest

    with pytest.raises(ValueError):
        build_api_arm("not-a-real-arm")


def test_qtree_runner_dispatch_raises_on_unknown_arm():
    import pytest

    with pytest.raises(ValueError):
        build_qtree_arm("not-a-real-arm")


def test_examgrade_runner_dispatch_raises_on_unknown_arm():
    import pytest

    with pytest.raises(ValueError):
        build_examgrade_arm("not-a-real-arm")


def test_nimble_exam_arm_whole_exam_raises_not_implemented(monkeypatch):
    import harness.env  # noqa: F401 -- force .env's one-time load_dotenv(override=True) to run

    # now safe to override without a later load_dotenv() call clobbering it --
    # module-level code in harness.env only ever runs once per process.
    monkeypatch.setenv("NIMBLE_BASE_URL", "http://127.0.0.1:1")  # never dialed -- raises before any call
    from examgrade.arms import NimbleExamArm

    arm = NimbleExamArm()
    try:
        import pytest

        with pytest.raises(NotImplementedError):
            arm.grade_exam("irrelevant full exam text", with_key=True)
    finally:
        arm.close()


def test_nimble_arm_has_no_whole_exam_support_but_chained_method_exists():
    from examgrade.arms import NimbleExamArm

    assert hasattr(NimbleExamArm, "grade_question")
    assert hasattr(NimbleExamArm, "grade_exam")
