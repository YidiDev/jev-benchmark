from harness.calibration import apply_temperature, ece, fit_temperature


def test_ece_empty_is_zero():
    assert ece([]) == 0.0


def test_ece_perfect_calibration_is_zero():
    # confidence exactly matches empirical accuracy in every bin
    pairs = [(0.9, True)] * 90 + [(0.9, False)] * 10
    assert ece(pairs, n_bins=10) < 1e-9


def test_ece_detects_overconfidence():
    # always 0.99 confident, but only right half the time -> large ECE
    pairs = [(0.99, True)] * 50 + [(0.99, False)] * 50
    e = ece(pairs, n_bins=10)
    assert e > 0.4


def test_apply_temperature_identity_at_one():
    for c in (0.1, 0.5, 0.9):
        assert abs(apply_temperature(c, 1.0) - c) < 1e-9


def test_apply_temperature_sharpens_below_one():
    # T < 1 should push confidence away from 0.5
    c = 0.7
    sharpened = apply_temperature(c, 0.5)
    assert sharpened > c


def test_apply_temperature_flattens_above_one():
    c = 0.7
    flattened = apply_temperature(c, 2.0)
    assert 0.5 < flattened < c


def test_fit_temperature_empty_defaults_to_one():
    assert fit_temperature([]) == 1.0


def test_fit_temperature_improves_or_matches_raw_ece():
    # overconfident-but-consistent miscalibration: a well-chosen fixed T
    # should never make ECE worse than leaving T=1.
    pairs = [(0.95, True)] * 60 + [(0.95, False)] * 40
    raw = ece(pairs)
    t = fit_temperature(pairs)
    fitted = ece([(apply_temperature(c, t), correct) for c, correct in pairs])
    assert fitted <= raw + 1e-9
