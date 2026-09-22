from arms.base import Prediction


def test_prediction_defaults():
    p = Prediction(folder="tax")
    assert p.probabilities == {}
    assert p.confidence is None
    assert p.latency_ms == 0.0
    assert p.input_tokens == 0
    assert p.output_tokens == 0


def test_prediction_carries_provided_fields():
    p = Prediction(
        folder="invoices",
        probabilities={"invoices": 0.7, "tax": 0.3},
        confidence=0.7,
        latency_ms=42.0,
        input_tokens=100,
        output_tokens=5,
    )
    assert p.folder == "invoices"
    assert p.probabilities["invoices"] == 0.7
    assert p.confidence == 0.7
    assert p.latency_ms == 42.0
    assert p.input_tokens == 100
    assert p.output_tokens == 5
