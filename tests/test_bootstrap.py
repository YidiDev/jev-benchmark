from harness.bootstrap import bootstrap_ci


def test_empty_returns_zero():
    assert bootstrap_ci([], purpose="test::empty") == (0.0, 0.0)


def test_all_true_gives_tight_ci_at_one():
    values = [True] * 100
    lo, hi = bootstrap_ci(values, purpose="test::all_true")
    assert lo == 1.0
    assert hi == 1.0


def test_all_false_gives_tight_ci_at_zero():
    values = [False] * 100
    lo, hi = bootstrap_ci(values, purpose="test::all_false")
    assert lo == 0.0
    assert hi == 0.0


def test_mixed_ci_brackets_the_point_estimate():
    values = [True] * 70 + [False] * 30
    lo, hi = bootstrap_ci(values, purpose="test::mixed")
    assert lo < 0.7 < hi
    assert 0.0 <= lo <= hi <= 1.0


def test_reproducible_given_same_purpose():
    values = [True] * 60 + [False] * 40
    a = bootstrap_ci(values, purpose="test::repro")
    b = bootstrap_ci(values, purpose="test::repro")
    assert a == b


def test_different_purpose_can_give_different_result():
    values = [True] * 55 + [False] * 45
    a = bootstrap_ci(values, purpose="test::purpose_a")
    b = bootstrap_ci(values, purpose="test::purpose_b")
    # Not guaranteed different, but overwhelmingly likely with n_boot=2000;
    # if this ever flakes it indicates the seed derivation collapsed, which
    # would itself be a bug worth catching.
    assert a != b
