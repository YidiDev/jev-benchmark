"""Real (not mocked) smoke test for arms/laya.py -- laya runs entirely
in-process on CPU with no network/API key needed, so unlike kev/nimble/clm
(self-hosted on a rented GPU, unavailable in this repo's own test
environment) it's cheap and safe to exercise directly, same as
tests/test_ground_truth.py-style real-data tests elsewhere in this repo.
Downloads convaiinnovations/laya from the Hub on first run (~small, cached
after); skipped if that's not reachable so `pytest` still passes offline.
"""

import pytest

from rubrics.clauses import build_rubric


@pytest.fixture(scope="module")
def laya_arm():
    try:
        from arms.laya import LayaArm
    except Exception as e:  # pragma: no cover -- offline / laya not installed
        pytest.skip(f"laya not available: {e}")
    try:
        return LayaArm()
    except Exception as e:  # pragma: no cover -- offline, can't fetch the checkpoint
        pytest.skip(f"could not load laya checkpoint: {e}")


def test_laya_predicts_a_known_folder(laya_arm):
    rubric = build_rubric(1, "A")
    doc_text = "Please find attached our invoice for services rendered this quarter."
    pred = laya_arm.predict(doc_text, rubric)
    assert pred.folder in rubric.folders
    assert 0.0 <= pred.confidence <= 1.0
    assert set(pred.probabilities.keys()) == set(rubric.folders)
    assert abs(sum(pred.probabilities.values()) - 1.0) < 1e-3
    assert pred.input_tokens > 0
    assert pred.latency_ms >= 0
