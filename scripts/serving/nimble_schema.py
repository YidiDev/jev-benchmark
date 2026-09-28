"""Pure translation logic between TypeSafe's question shape and Nimble's
flat enum/boolean schema -- factored out of nimble_server.py (which needs
fastapi/uvicorn, only installed on the rented GPU box, not a dependency of
this repo's own test environment) so it can be unit-tested with no extra
dependencies. See scripts/serving/nimble_server.py's module docstring for
the full rationale and the verified Nimble API contract this maps to/from.
"""

from __future__ import annotations

from typing import Any


def to_nimble_field(question: dict[str, Any]) -> tuple[dict[str, Any], str, list[str] | None]:
    """TypeSafe question dict -> (nimble_field_schema, qtype, ordered_choice_keys_or_None)."""
    qtype = question["type"]
    instructions = question.get("instructions", "")

    if qtype == "choice":
        criteria = question["criteria"]
        choices = list(criteria.keys())
        return (
            {
                "type": "enum",
                "choices": choices,
                "description": instructions,
                "choice_descriptions": {k: (v or "") for k, v in criteria.items()},
            },
            qtype,
            choices,
        )
    if qtype == "noul":
        return ({"type": "boolean", "description": instructions}, qtype, None)
    if qtype == "score":
        levels = question["criteria"]  # ordered list, index 0 = lowest
        keys = [str(i) for i in range(len(levels))]
        return (
            {
                "type": "enum",
                "choices": keys,
                "description": instructions,
                "choice_descriptions": {str(i): levels[i] for i in range(len(levels))},
            },
            qtype,
            keys,
        )
    raise ValueError(f"unsupported question type {qtype!r}")


def score_confidence(levels_probs: list[float]) -> float:
    """max(0, 1 - E|level - mode| / D); D is a uniform distribution's mean
    distance from its middle. Mirrors arms/kev.py's/Jev's Score confidence
    (the formula Kev's README cites as matching TypeSafe's reference
    adapter)."""
    n = len(levels_probs)
    if n <= 1:
        return 1.0
    mode = max(range(n), key=lambda i: levels_probs[i])
    e_dist = sum(p * abs(i - mode) for i, p in enumerate(levels_probs))
    mid = (n - 1) / 2
    d = sum(abs(i - mid) for i in range(n)) / n
    if d == 0:
        return 1.0
    return max(0.0, 1.0 - e_dist / d)


def choice_confidence(p_max: float, k: int) -> float:
    """(p_max - 1/K) / (1 - 1/K); TypeSafe's reference Choice confidence
    formula (same one arms/kev.py's README source documents)."""
    if k <= 1:
        return 1.0
    return (p_max - 1 / k) / (1 - 1 / k)


def translate_result(
    result: dict[str, Any],
    qtypes: dict[str, str],
    choice_keys: dict[str, list[str] | None],
    score_criteria: dict[str, list[str]],
) -> tuple[dict[str, Any], int]:
    """Nimble's raw `scorer.score()` result -> TypeSafe-shaped `answers`
    dict, plus total input tokens consumed across all fields."""
    answers: dict[str, Any] = {}
    total_input_tokens = 0
    for qid, field_result in result["fields"].items():
        qtype = qtypes[qid]
        scores: dict[str, float] = field_result["scores"]
        total_input_tokens += field_result.get("prompt_token_count", 0)

        if qtype == "noul":
            p_true = scores.get("true", scores.get("True", 0.0))
            answers[qid] = {"type": "noul", "noul": p_true}
        elif qtype == "choice":
            keys = choice_keys[qid]
            p_max = max(scores.values())
            answers[qid] = {
                "type": "choice",
                "choice": field_result["value"],
                "probabilities": scores,
                "confidence": choice_confidence(p_max, len(keys)),
            }
        else:  # score
            keys = choice_keys[qid]
            ordered_probs = [scores[k] for k in keys]
            expected = sum(i * p for i, p in enumerate(ordered_probs))
            answers[qid] = {
                "type": "score",
                "score": expected,
                "legend": dict(zip(keys, score_criteria[qid])),
                "probabilities": dict(zip(keys, ordered_probs)),
                "confidence": score_confidence(ordered_probs),
            }
    return answers, total_input_tokens
