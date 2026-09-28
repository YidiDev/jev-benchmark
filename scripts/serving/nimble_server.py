"""Thin FastAPI wrapper giving `bespokelabs/Bespoke-Nimble-9B` a TypeSafe-
shaped `/v1/systemone` endpoint, so `arms/nimble.py` can use the same
`typesafe_sdk.TypeSafeClient` every other arm in this benchmark uses.

Why this exists: Nimble's own repo (github.com/bespokelabsai/nimble) ships
`nimble.scoring.cuda_scorer.CudaCandidateScorer` as an in-process Python
class only -- no bundled HTTP server. (A TypeSafe-shaped `/v1/systemone` demo
*does* exist, but only as the authors' own Modal+SGLang deployment
(`docs/MODAL_SERVING.md`), which is Modal-specific infra we are not using --
we're on a plain rented GPU box, see methodology.md §18.) This file is that
missing piece: a direct, from-scratch HTTP wrapper around the *documented*
Python API (`CudaCandidateScorer.__init__(**config)` /
`.score(context, schema, mode="independent")`), verified against
nimble/scoring/cuda_scorer.py and the repo README directly (2026-09-26).

Runs ON the rented GPU box (not on this repo's own machine -- see
scripts/serving/nimble_setup.sh for how it gets there and is launched).

Schema translation (TypeSafe question -> Nimble's flat enum/boolean schema):
  - "choice" -> {"type": "enum", "choices": [...], "description": instructions,
                 "choice_descriptions": criteria}
  - "noul"   -> {"type": "boolean", "description": instructions}
  - "score"  -> {"type": "enum", "choices": ["0", "1", ..., "N-1"],
                 "description": instructions,
                 "choice_descriptions": {"0": level_0_text, ...}}
    (Nimble's schema has no native ordered/rating type -- its own README
    says exactly this: "If a field is an ordered rating scale, your
    application can use the probabilities to calculate an expected level."
    This wrapper does that calculation, the same expected-value-over-levels
    approach arms/kev.py's Score handling and Jev's own Score primitive use.)

Confidence, since CudaCandidateScorer.score() returns raw per-candidate
probabilities/logits but no confidence scalar of its own, is computed with
the same formula Kev's README cites as "the ones in TypeSafe's reference
adapter" (system-one-adapter 0.2.1): choice confidence
`(p_max - 1/K) / (1 - 1/K)`; score confidence
`max(0, 1 - E|level - mode| / D)` with `D` the mean distance of a uniform
distribution over the levels from its middle.

One HTTP request = one `scorer.score(state, schema)` call with every
question's field in the same schema dict -- the CUDA scorer's own docstring
says it scores each field separately with the full prompt each time either
way, so batching questions into one schema dict costs the same as separate
calls but keeps this wrapper's request/response shape aligned with every
other arm's one-call-per-document pattern.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="nimble-systemone-wrapper")

_scorer = None
_model_name = "nimble-latest"


def _load_scorer():
    global _scorer
    if _scorer is not None:
        return _scorer
    from nimble.scoring.cuda_scorer import CudaCandidateScorer

    config_path = Path(os.environ.get("NIMBLE_MODEL_CONFIG", ".cache/nimble-model.json"))
    config = json.loads(config_path.read_text())
    _scorer = CudaCandidateScorer(**config)
    return _scorer


class SystemOneRequest(BaseModel):
    state: Any
    model: str | None = None
    questions: dict[str, dict[str, Any]]


def _to_nimble_field(question: dict[str, Any]) -> tuple[dict[str, Any], str, list[str] | None]:
    """Returns (nimble_field_schema, qtype, ordered_choice_keys_or_None)."""
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
    raise HTTPException(422, f"unsupported question type {qtype!r}")


def _score_confidence(levels_probs: list[float]) -> float:
    """max(0, 1 - E|level - mode| / D); D is a uniform distribution's mean
    distance from its middle. Mirrors arms/kev.py's/Jev's Score confidence."""
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


@app.post("/v1/systemone")
def system_one(req: SystemOneRequest):
    scorer = _load_scorer()

    schema: dict[str, Any] = {}
    qtypes: dict[str, str] = {}
    choice_keys: dict[str, list[str] | None] = {}
    for qid, question in req.questions.items():
        field, qtype, keys = _to_nimble_field(question)
        schema[qid] = field
        qtypes[qid] = qtype
        choice_keys[qid] = keys

    if isinstance(req.state, (dict, list)):
        context = json.dumps(req.state, ensure_ascii=False)
    else:
        context = str(req.state)

    start = time.perf_counter()
    result = scorer.score(context, schema)
    latency_ms = (time.perf_counter() - start) * 1000

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
            k = len(keys)
            confidence = (p_max - 1 / k) / (1 - 1 / k) if k > 1 else 1.0
            answers[qid] = {
                "type": "choice",
                "choice": field_result["value"],
                "probabilities": scores,
                "confidence": confidence,
            }
        else:  # score
            keys = choice_keys[qid]
            ordered_probs = [scores[k] for k in keys]
            expected = sum(i * p for i, p in enumerate(ordered_probs))
            answers[qid] = {
                "type": "score",
                "score": expected,
                "legend": {k: v for k, v in zip(keys, req.questions[qid]["criteria"])},
                "probabilities": {k: p for k, p in zip(keys, ordered_probs)},
                "confidence": _score_confidence(ordered_probs),
            }

    return {
        "model": req.model or _model_name,
        "answers": answers,
        "usage": {"input_tokens": total_input_tokens, "output_tokens": 0},
        "latency_ms": latency_ms,
    }


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _scorer is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("NIMBLE_PORT", "8010")))
