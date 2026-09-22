"""jev arm -- the subject of this benchmark.

Uses the official `typesafe-sdk` against `https://api.typesafe.ai`, model
`jev-latest` (resolves to `jev-1.13.0` as of 2026-09-21, see
methodology.md §0). One `Choice` question per document: `criteria` is the
rubric's full folder-name -> description mapping, `instructions` is the
full rule text, `state` is the raw document text -- the exact decomposition
frozen in `rubrics/clauses.py` and applied identically to every arm
(test-plan.md §8 discipline). Unlike nli-bart/emb-bge, Jev sees the entire
rubric, not just folder display names.

Every call is logged through `harness.spend_ledger.record_spend` even
though Jev's own budget isn't constrained the way the Anthropic budget is
(output tokens are free; input is $0.042/Mtok, negligible at this corpus
size) -- test-plan.md's "track pricing as we go" instruction applies to
every paid call, not just the ones near a hard limit.
"""

from __future__ import annotations

import time

from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401  -- loads .env (TYPESAFE_API_KEY) before client init
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "jev-latest"
PRICING_KEY = "jev-latest"


class JevArm(Arm):
    name = "jev"

    def __init__(self, model: str = MODEL, spend_source: str = "jev_arm"):
        self._client = TypeSafeClient(model=model)
        self._model = model
        self._spend_source = spend_source

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        criteria = {folder: rubric.criteria[folder] for folder in rubric.folders}
        question = Choice(instructions=rubric.instructions, criteria=criteria)

        start = time.perf_counter()
        response = self._client.system_one(
            state=doc_text,
            questions={"folder": question},
        )
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["folder"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model=PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"clause_type={rubric.clause_type} condition={rubric.condition}",
        )

        return Prediction(
            folder=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
