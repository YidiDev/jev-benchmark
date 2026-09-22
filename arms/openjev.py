"""openjev arm -- the fallback-viability question (test-plan.md Part 3):
if TypeSafe's hosted Jev ever became unavailable, is there a genuinely
viable open-source, self-hostable substitute?

`razorback16/openjev` speaks Jev's exact wire API (same `/v1/systemone`
request/response shape), so the official `typesafe-sdk` works unchanged
against it -- just point `base_url` at a server running it. Used here via
the free-hosted Codiv endpoint (`https://api.codiv.ai`, model alias
`openjev-latest`, reports itself as `openjev-0.1`) rather than local
self-hosting, which isn't feasible on this machine (RTX 3050 8GB, well
under OpenJev's 24GB-class GPU requirement; not Apple silicon either, so
the MLX path is also unavailable -- see methodology.md §0).

Structurally identical to arms/jev.py (same Choice decomposition, same
state/instructions/criteria shape) -- the whole point of testing this arm
is that it's a drop-in replacement, so the harness code should look like
one too. Codiv's free tier means every call here costs $0 and never
touches the Anthropic budget (PRICING["openjev"] is $0/$0 in
harness/constants.py), but every call is still logged through
record_spend for consistency and so real latency/token numbers are
captured even though cost isn't.
"""

from __future__ import annotations

import os
import time

from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401 -- loads .env (CODIV_API_KEY/CODIV_BASE_URL) before client init
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "openjev-latest"
PRICING_KEY = "openjev"


class OpenJevArm(Arm):
    name = "openjev"

    def __init__(self, model: str = MODEL, spend_source: str = "openjev_arm"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["CODIV_BASE_URL"],
            api_key=os.environ["CODIV_API_KEY"],
        )
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

    def __enter__(self) -> "OpenJevArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
