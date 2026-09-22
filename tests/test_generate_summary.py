from scripts.generate_summary import build_summary, flatten


def test_build_summary_structure():
    summary = build_summary()
    assert set(summary.keys()) == {"ct1_8", "ct9", "ct10", "spend"}
    assert summary["ct1_8"] is not None
    assert "jev" in summary["ct1_8"]["arms"]
    assert summary["ct9"] is not None
    assert "jev" in summary["ct9"]["arms"]
    assert summary["ct10"] is not None
    assert "jev" in summary["ct10"]["arms"]
    assert summary["spend"]["anthropic_cumulative_usd"] > 0


def test_flatten_produces_rows_with_expected_schema():
    summary = build_summary()
    rows = flatten(summary)
    assert len(rows) > 0
    expected_keys = {"section", "arm", "metric", "clause_type", "condition", "k", "labeling", "value", "n", "extra"}
    for row in rows[:20]:
        assert set(row.keys()) == expected_keys


def test_flatten_covers_all_sections():
    summary = build_summary()
    rows = flatten(summary)
    sections = {r["section"] for r in rows}
    assert "ct1_8" in sections
    assert "ct9" in sections
    assert "ct10" in sections
    assert "spend" in sections
