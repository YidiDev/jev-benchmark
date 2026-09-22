from qtree.questions import (
    SPECIAL_OUTCOMES,
    SPECIAL_QUESTIONS,
    STANDARD_QUESTIONS,
    binary_value,
    sample_form_answers,
    sample_special_answers,
    sample_standard_answers,
    special_outcome,
)


def test_binary_value_plain_yes_no():
    assert binary_value("q01", "yes") is True
    assert binary_value("q01", "no") is False


def test_binary_value_multiway_cuts():
    assert binary_value("q03", "0-1") is False
    assert binary_value("q03", "2-4") is False
    assert binary_value("q03", "5-9") is True
    assert binary_value("q03", "10+") is True


def test_special_outcome_all_four_combinations():
    assert special_outcome(True, True) == "compliant_correct"
    assert special_outcome(True, False) == "noncompliant_correct"
    assert special_outcome(False, True) == "compliant_wrong"
    assert special_outcome(False, False) == "noncompliant_wrong"
    assert set(SPECIAL_OUTCOMES) == {
        special_outcome(c, l) for c in (True, False) for l in (True, False)
    }


def test_sample_standard_answers_covers_every_question():
    import random

    rng = random.Random(42)
    answers = sample_standard_answers(rng)
    assert set(answers.keys()) == {q.id for q in STANDARD_QUESTIONS}
    for q in STANDARD_QUESTIONS:
        assert answers[q.id] in q.options


def test_sample_special_answers_structure():
    import random

    rng = random.Random(42)
    answers = sample_special_answers(rng)
    assert set(answers.keys()) == {q.id for q in SPECIAL_QUESTIONS}
    for q in SPECIAL_QUESTIONS:
        bits = answers[q.id]
        assert isinstance(bits["content_correct"], bool)
        assert isinstance(bits["length_compliant"], bool)


def test_sample_form_answers_reproducible():
    a = sample_form_answers("qt_test_reproducibility_001")
    b = sample_form_answers("qt_test_reproducibility_001")
    assert a == b


def test_sample_form_answers_differs_across_forms():
    a = sample_form_answers("qt_test_form_a")
    b = sample_form_answers("qt_test_form_b")
    assert a != b
