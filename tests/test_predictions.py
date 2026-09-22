from harness.predictions import (
    PredictionRecord,
    append_prediction,
    existing_keys,
    load_predictions,
)


def test_append_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.predictions.PREDICTIONS_DIR", tmp_path)
    record = PredictionRecord(
        arm="test-arm",
        doc_id="ct1_te_001",
        clause_type=1,
        condition="A",
        split="test",
        repeat=1,
        predicted_folder="tax",
        probabilities={"tax": 0.9, "invoices": 0.05, "contracts": 0.05},
        confidence=0.9,
        latency_ms=12.3,
    )
    append_prediction(record)

    loaded = load_predictions("test-arm")
    assert len(loaded) == 1
    assert loaded[0] == record


def test_load_predictions_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.predictions.PREDICTIONS_DIR", tmp_path)
    assert load_predictions("nonexistent-arm") == []


def test_existing_keys_resumability(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.predictions.PREDICTIONS_DIR", tmp_path)
    r1 = PredictionRecord(
        arm="a", doc_id="d1", clause_type=1, condition="A", split="test", repeat=1, predicted_folder="x"
    )
    r2 = PredictionRecord(
        arm="a", doc_id="d2", clause_type=1, condition="B", split="test", repeat=1, predicted_folder="y"
    )
    append_prediction(r1)
    append_prediction(r2)

    keys = existing_keys("a")
    assert keys == {("d1", "A", 1), ("d2", "B", 1)}
    assert ("d3", "A", 1) not in keys


def test_predictions_for_different_arms_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("harness.predictions.PREDICTIONS_DIR", tmp_path)
    append_prediction(
        PredictionRecord(
            arm="arm-one", doc_id="d1", clause_type=1, condition="A", split="test", repeat=1, predicted_folder="x"
        )
    )
    append_prediction(
        PredictionRecord(
            arm="arm-two", doc_id="d1", clause_type=1, condition="A", split="test", repeat=1, predicted_folder="y"
        )
    )
    assert len(load_predictions("arm-one")) == 1
    assert len(load_predictions("arm-two")) == 1
    assert load_predictions("arm-one")[0].predicted_folder == "x"
    assert load_predictions("arm-two")[0].predicted_folder == "y"
