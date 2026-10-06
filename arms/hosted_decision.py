"""Shared transport for self-hosted decision servers; compute billed separately."""
from __future__ import annotations

import os
import time

from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401 -- load .env before credentials
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric


class HostedDecisionArm(Arm):
    MODEL: str
    PRICING_KEY: str
    ENV_PREFIX: str

    def __init__(self, model: str | None = None, spend_source: str | None = None):
        self._client = TypeSafeClient(
            model=model or self.MODEL,
            base_url=os.environ[f"{self.ENV_PREFIX}_BASE_URL"],
            api_key=os.environ.get(f"{self.ENV_PREFIX}_API_KEY") or "local",
            # CUDA kernel autotuning can exceed the SDK's 10-second default.
            # Allow it to finish before a retry could overlap mutable engine state.
            timeout=600.0,
        )
        self._spend_source = spend_source or f"{self.name}_arm"

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        question = Choice(instructions=rubric.instructions,
                          criteria={f: rubric.criteria[f] for f in rubric.folders})
        start = time.perf_counter()
        response = self._client.system_one(state=doc_text, questions={"folder": question})
        latency_ms = (time.perf_counter() - start) * 1000
        answer = response.choices["folder"]
        input_tokens = response.usage.input_tokens or 0
        output_tokens = response.usage.output_tokens or 0
        record_spend(source=self._spend_source, model=self.PRICING_KEY,
                     input_tokens=input_tokens, output_tokens=output_tokens,
                     note=f"clause_type={rubric.clause_type} condition={rubric.condition}")
        return Prediction(folder=answer.choice, probabilities=dict(answer.probabilities),
                          confidence=answer.confidence, latency_ms=latency_ms,
                          input_tokens=input_tokens, output_tokens=output_tokens)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
