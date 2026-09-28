"""laya arm: convaiinnovations/laya, a non-autoregressive ModernBERT-large
(421M) encoder + decision head, run in-process via the `laya` pip package
(github.com/NandhaKishorM/laya, PyPI `laya`).

Deliberately the "floor" datapoint in this benchmark (see methodology.md):
the smallest and most context-limited of the four arms added alongside
Kev-4B/Nimble-9B/CLM-8B. Two properties matter for interpreting its results:

1. It reads real rubric text (Choice `instructions`/`criteria`, same
   decomposition as every other arm here -- see arms/base.py), unlike
   nli-bart/emb-bge, which never see rubric text at all. So it is scored
   like jev/haiku/openjev/sonnet (a real SHUFFLE run, CALIBRATION_ARMS
   eligible), not like the local instrument arms.
2. Its checkpoint's default `max_len` is 512 tokens (`rl_agent_config.json`,
   read at load time -- see laya.agent.Agent.__init__ / _encode_state).
   Longer documents are truncated by laya's own tokenizer-level truncation
   inside `build_sequence`, not rejected -- so CT8 (long-context distractor,
   documents padded well past 512 tokens) is expected to genuinely lose the
   distinguishing content for this arm rather than error out. This is the
   whole point of choosing Laya as the floor model: a hard, real context
   ceiling lower than every other arm in the benchmark.

Runs entirely on CPU on this machine (421M params) -- no GPU, no rented
compute, no per-token billing. Real cost is $0.00 like nli-bart/emb-bge, but
unlike those two, Laya is priced in SELF_HOSTED_PRICING too (harness/
constants.py) since it's a genuine self-hostable model, not just an
instrument -- see methodology.md §17 for the self-hosted-cost-estimate
convention this follows.
"""

from __future__ import annotations

import time

from laya import load

from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL_ID = "convaiinnovations/laya"
PRICING_KEY = "laya"


class LayaArm(Arm):
    name = "laya"

    def __init__(self, model_id: str = MODEL_ID, device: str | None = None, spend_source: str = "laya_arm"):
        self._agent = load(model_id, device=device or "cpu")
        self._spend_source = spend_source

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        criteria = {folder: rubric.criteria[folder] for folder in rubric.folders}
        question = {
            "type": "choice",
            "instructions": rubric.instructions,
            "criteria": criteria,
        }

        start = time.perf_counter()
        response = self._agent.system_one(state=doc_text, questions={"folder": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response["answers"]["folder"]
        usage = response["usage"]
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]

        # Real cost is $0.00 (runs on this machine's own CPU, no per-token
        # billing -- PRICING["laya"] is 0/0), but logged through record_spend
        # anyway, same rationale as arms/openjev.py: captures real token
        # counts so the self-hosted cost estimate (methodology.md §17) can be
        # derived from actual logged usage rather than re-tokenizing after
        # the fact, the way nli-bart/emb-bge's estimate had to be.
        record_spend(
            source=self._spend_source,
            model=PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"clause_type={rubric.clause_type} condition={rubric.condition}",
        )

        return Prediction(
            folder=answer["choice"],
            probabilities=dict(answer["probabilities"]),
            confidence=answer["confidence"],
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
