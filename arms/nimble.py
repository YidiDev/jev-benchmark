"""nimble arm: bespokelabs/Bespoke-Nimble-9B, a LoRA fine-tune of
Qwen3.5-9B trained via "contrastive data curation" (paired examples
differing in one flipping fact) on only 2,676 examples across ten
categories (github.com/bespokelabsai/nimble). Tests whether that narrow,
curated training generalizes off-distribution or collapses on this
benchmark's CT5/CT6 ("hard mode": computed thresholds, temporal reasoning)
-- clause types with no obvious analogue among Nimble's own ten training
categories.

Nimble's own README/model card reports 90.12% reference-agreement on its
324-example holdout vs Jev 1.13.0's 93.21% -- a real but modest gap on its
*own* distribution; this benchmark measures the gap under conditions Nimble
never curated data for.

Nimble ships no HTTP server of its own (the Python `CudaCandidateScorer`
class is in-process only -- see scripts/serving/nimble_server.py's
docstring for the full explanation and why a from-scratch FastAPI wrapper
was written instead of using the authors' Modal-specific SGLang demo). That
wrapper implements the same `/v1/systemone` wire shape as Jev/OpenJev/Kev,
so this arm is structurally identical to arms/kev.py -- same TypeSafeClient
usage, just pointed at `NIMBLE_BASE_URL`.

**Scope note**: full CT1-9 + CT10 chained-mode grading only. CT10's
whole-exam mode (30 Score questions in one call) is explicitly marked
unsupported for Nimble, not silently skipped -- its own docs cap requests at
8,192 prompt tokens (`NIMBLE_MAX_PROMPT_TOKENS`), and a full 30-question AP
World History exam transcript plus 30 rubrics routinely exceeds that (see
examgrade/arms.py's NimbleExamArm, which raises NotImplementedError from
`grade_exam` with this exact reasoning, and methodology.md §18 for the
supporting token-count evidence). Self-hosted via a custom FastAPI wrapper
(scripts/serving/nimble_server.py) on the same rented GPU as Kev-4B and
CLM-8B; every call logged through record_spend even though PRICING
["nimble-9b"] is $0/$0, same convention as every other self-hosted arm.
"""

from __future__ import annotations

import os
import time

from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401 -- loads .env (NIMBLE_BASE_URL) before client init
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "nimble-latest"
PRICING_KEY = "nimble-9b"


class NimbleArm(Arm):
    name = "nimble"

    def __init__(self, model: str = MODEL, spend_source: str = "nimble_arm"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["NIMBLE_BASE_URL"],
            api_key=os.environ.get("NIMBLE_API_KEY") or "local",
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

    def __enter__(self) -> "NimbleArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
