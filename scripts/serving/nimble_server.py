"""Thin FastAPI wrapper giving `bespokelabs/Bespoke-Nimble-9B` a TypeSafe-
shaped `/v1/systemone` endpoint, so `arms/nimble.py` can use the same
`typesafe_sdk.TypeSafeClient` every other arm in this benchmark uses.

Why this exists: Nimble's own repo (github.com/bespokelabsai/nimble) ships
`nimble.scoring.cuda_scorer.CudaCandidateScorer` as an in-process Python
class only -- no bundled HTTP server. (A TypeSafe-shaped `/v1/systemone`
demo *does* exist, but only as the authors' own Modal+SGLang deployment
(`docs/MODAL_SERVING.md`), which is Modal-specific infra we are not using --
we're on a plain rented GPU box, see methodology.md §18.) This file is that
missing piece: a direct, from-scratch HTTP wrapper around the *documented*
Python API (`CudaCandidateScorer.__init__(**config)` /
`.score(context, schema, mode="independent")`), verified against
nimble/scoring/cuda_scorer.py and the repo README directly (2026-09-26).

Runs ON the rented GPU box (not on this repo's own machine -- see
scripts/serving/nimble_setup.sh for how it gets there and is launched). The
request/response translation logic (TypeSafe question shape <-> Nimble's
flat enum/boolean schema) lives in scripts/serving/nimble_schema.py, which
has no fastapi/uvicorn dependency and is unit-tested directly in
tests/test_nimble_schema.py -- this file is just the HTTP plumbing around
it, since fastapi/uvicorn are only ever installed on the rented GPU box, not
part of this repo's own dependencies (see pyproject.toml).

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

from fastapi import FastAPI
from pydantic import BaseModel

from nimble_schema import to_nimble_field, translate_result

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


@app.post("/v1/systemone")
def system_one(req: SystemOneRequest):
    scorer = _load_scorer()

    schema: dict[str, Any] = {}
    qtypes: dict[str, str] = {}
    choice_keys: dict[str, list[str] | None] = {}
    score_criteria: dict[str, list[str]] = {}
    for qid, question in req.questions.items():
        field, qtype, keys = to_nimble_field(question)
        schema[qid] = field
        qtypes[qid] = qtype
        choice_keys[qid] = keys
        if qtype == "score":
            score_criteria[qid] = question["criteria"]

    context = json.dumps(req.state, ensure_ascii=False) if isinstance(req.state, (dict, list)) else str(req.state)

    start = time.perf_counter()
    result = scorer.score(context, schema)
    latency_ms = (time.perf_counter() - start) * 1000

    answers, total_input_tokens = translate_result(result, qtypes, choice_keys, score_criteria)

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
