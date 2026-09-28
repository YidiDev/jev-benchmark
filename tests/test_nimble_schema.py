"""Unit tests for scripts/serving/nimble_schema.py's pure TypeSafe<->Nimble
translation logic -- no fastapi/uvicorn/GPU/network needed, unlike
nimble_server.py itself (which only ever runs on the rented GPU box, see
that file's docstring)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "serving"))

from nimble_schema import choice_confidence, score_confidence, to_nimble_field, translate_result  # noqa: E402


def test_to_nimble_field_choice():
    question = {
        "type": "choice",
        "instructions": "Which folder?",
        "criteria": {"tax": "Tax documents", "hr": "HR documents"},
    }
    field, qtype, keys = to_nimble_field(question)
    assert qtype == "choice"
    assert keys == ["tax", "hr"]
    assert field == {
        "type": "enum",
        "choices": ["tax", "hr"],
        "description": "Which folder?",
        "choice_descriptions": {"tax": "Tax documents", "hr": "HR documents"},
    }


def test_to_nimble_field_noul():
    question = {"type": "noul", "instructions": "Is this urgent?"}
    field, qtype, keys = to_nimble_field(question)
    assert qtype == "noul"
    assert keys is None
    assert field == {"type": "boolean", "description": "Is this urgent?"}


def test_to_nimble_field_score():
    question = {"type": "score", "instructions": "Grade this.", "criteria": ["low", "medium", "high"]}
    field, qtype, keys = to_nimble_field(question)
    assert qtype == "score"
    assert keys == ["0", "1", "2"]
    assert field["type"] == "enum"
    assert field["choices"] == ["0", "1", "2"]
    assert field["choice_descriptions"] == {"0": "low", "1": "medium", "2": "high"}


def test_to_nimble_field_unsupported_type():
    import pytest

    with pytest.raises(ValueError):
        to_nimble_field({"type": "unknown", "instructions": "x"})


def test_choice_confidence_formula():
    # (p_max - 1/K) / (1 - 1/K)
    assert choice_confidence(1.0, 2) == 1.0
    assert choice_confidence(0.5, 2) == 0.0
    assert abs(choice_confidence(0.75, 4) - (0.75 - 0.25) / 0.75) < 1e-9
    assert choice_confidence(1.0, 1) == 1.0  # single option is always fully confident


def test_score_confidence_all_mass_on_mode_is_one():
    assert score_confidence([0.0, 1.0, 0.0]) == 1.0


def test_score_confidence_uniform_is_zero():
    assert score_confidence([1 / 3, 1 / 3, 1 / 3]) == 0.0


def test_score_confidence_single_level_is_one():
    assert score_confidence([1.0]) == 1.0


def test_translate_result_choice_and_score_and_noul():
    result = {
        "fields": {
            "folder": {"value": "tax", "scores": {"tax": 0.8, "hr": 0.2}, "prompt_token_count": 50},
            "urgent": {"value": True, "scores": {"true": 0.9, "false": 0.1}, "prompt_token_count": 50},
            "quality": {"value": "1", "scores": {"0": 0.1, "1": 0.7, "2": 0.2}, "prompt_token_count": 50},
        }
    }
    qtypes = {"folder": "choice", "urgent": "noul", "quality": "score"}
    choice_keys = {"folder": ["tax", "hr"], "urgent": None, "quality": ["0", "1", "2"]}
    score_criteria = {"quality": ["low", "medium", "high"]}

    answers, total_tokens = translate_result(result, qtypes, choice_keys, score_criteria)

    assert total_tokens == 150
    assert answers["folder"]["type"] == "choice"
    assert answers["folder"]["choice"] == "tax"
    assert answers["folder"]["probabilities"] == {"tax": 0.8, "hr": 0.2}
    assert answers["urgent"]["type"] == "noul"
    assert answers["urgent"]["noul"] == 0.9
    assert answers["quality"]["type"] == "score"
    assert abs(answers["quality"]["score"] - (0 * 0.1 + 1 * 0.7 + 2 * 0.2)) < 1e-9
    assert answers["quality"]["legend"] == {"0": "low", "1": "medium", "2": "high"}
