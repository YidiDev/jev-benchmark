"""Regression test for the shuffle-control fix: rubric-reading API arms
(jev/haiku/openjev) must run a real SHUFFLE condition, unlike the local
label-text-only arms which correctly reuse Condition B (see
scripts/run_api_arm.py and scripts/run_arm.py docstrings for the full
reasoning, and methodology.md §8 for the incident writeup)."""

from harness.constants import CONDITIONS
from scripts.run_api_arm import API_ARM_CONDITIONS


def test_api_arm_conditions_include_shuffle():
    assert API_ARM_CONDITIONS == (*CONDITIONS, "SHUFFLE")
    assert "SHUFFLE" in API_ARM_CONDITIONS
    assert set(CONDITIONS) == {"A", "B", "C"}


def test_shuffle_rubric_text_differs_from_condition_b():
    """The whole reason SHUFFLE must be run separately for rubric-reading
    arms: the literal instructions text differs from Condition B's."""
    from rubrics.clauses import build_rubric

    for ct in (1, 2, 3, 4):
        b = build_rubric(ct, "B")
        shuffle = build_rubric(ct, "SHUFFLE")
        assert b.instructions != shuffle.instructions
        # Same opaque-id *set*, just reassigned -- this is what makes reuse
        # valid for label-text-only arms but invalid for rubric-readers.
        assert set(b.folders) == set(shuffle.folders)
        assert b.mapping != shuffle.mapping
