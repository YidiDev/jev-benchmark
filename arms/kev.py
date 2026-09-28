"""kev arm: jaredpalmer/kev's Kev-4B, a rank-16 LoRA adapter + pointer head
on Qwen3.5-4B-Base (github.com/jaredpalmer/kev), speaking Jev's exact
`/v1/systemone` wire API -- the official `typesafe_sdk` works against it
unchanged, same drop-in property as arms/openjev.py.

Kev-4B's own model card reports out-of-domain accuracy 0.817 (dev) / 0.838
(test) vs Jev's 0.857 on its `transfer-v4` suite -- within four points of Jev
on classification-shaped sources, closer than the "0.79 vs 0.86" figure that
motivated this addition, which was the *previous* Qwen3-based checkpoint
(`jaredpalmer/kev-4b@qwen3`, now superseded; see methodology.md §18). The
specific hypothesis this arm tests here is CT8 (long-context distractor):
Kev-4B trained on states of at most 384 tokens (1,024 combined with one
question) despite an 8,192-token *server* limit, so its own README already
documents accuracy dropping on buried/long documents relative to Kev-27B
(which was trained on exactly this failure mode). We do not run Kev-27B
(needs an 80GB-class GPU, out of scope for a $20 rented-GPU budget), so this
arm's CT8 result should be read as "does the smallest commonly-deployed Kev
size fix the context ceiling," not a claim about the Kev family generally.

Self-hosted via `kev.serve` on a rented GPU (see scripts/serving/kev_serve.sh
and methodology.md §18 for the provisioning/teardown log) -- NOT via
OpenRouter/SiliconFlow's pay-per-token listing, which does exist for this
model but was deliberately not used, to keep methodology identical across
all three self-hosted arms added alongside this one (Kev, Nimble, CLM) and
avoid a fourth billing surface. `KEV_BASE_URL` (see harness/env.py) points
at that server; every call is still logged through record_spend even though
PRICING["kev-4b"] is $0/$0, same convention as arms/openjev.py.
"""

from __future__ import annotations

import os
import time

from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401 -- loads .env (KEV_BASE_URL) before client init
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "kev-latest"
PRICING_KEY = "kev-4b"


class KevArm(Arm):
    name = "kev"

    def __init__(self, model: str = MODEL, spend_source: str = "kev_arm"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["KEV_BASE_URL"],
            api_key=os.environ.get("KEV_API_KEY") or "local",  # kev.serve's own default, see its README
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

    def __enter__(self) -> "KevArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
