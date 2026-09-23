"""sonnet arm -- a second, stronger reference point for Part 2's head-to-head
comparison (test-plan.md). Claude Sonnet 5, forced tool-use for constrained
`{folder_id, confidence}` output, identical rubric decomposition and prompt
shape to `arms/haiku.py`: one question per document, full rubric text, no
extra scaffolding or multi-pass prompting that Jev doesn't also get (§5.2
equal-effort budget).

**Why this exists.** A Sonnet comparison was proposed early in Part 2 (per
prior instruction, triggered by Haiku underperforming Jev) and explicitly
declined at the time -- methodology.md §11: "if jev did 100%, not worth
testing the other stuff." That call was reasonable when CT1-4 was the only
evidence (a clean Jev ceiling makes a third model close to uninformative).
It was revisited once CT9/CT10 existed and showed Haiku underperforming Jev
by a wider, more structurally interesting margin than CT1-8 ever did (e.g.
CT10 whole-exam mode MAE 0.30-0.33 vs Jev's 0.13-0.17) -- see methodology.md
for the dated log entry documenting this reversal and its cost accounting.

**Model note.** `claude-sonnet-5` (not `claude-sonnet-4-5`) is the exact
model ID confirmed live via `GET /v1/models` and already in production use
in this repo for corpus-authoring calls (`corpus/generate_prose.py`,
`qtree/generate_prose.py`, `examgrade/generate_prose.py`), all upstream
content-generation roles. This is the first time Sonnet is used downstream,
as a grading/classification arm rather than an author of the material being
graded.

Pricing: `claude-sonnet-5` is exactly 2x `claude-haiku-4-5`'s per-token rate
on both input and output (`harness/constants.py` PRICING table) -- verified
against provider docs the same way Haiku's rate was.

Deviations from `arms/haiku.py` are intentionally nil: same forced tool-use
pattern (malformed/refused response is a hard API-level failure, not a
silent parsing failure), same `folder_id` enum constraint mirroring Jev's
`Choice` primitive, same spend-ledger discipline. Caching was not
re-evaluated here (Haiku's cacheable-prefix analysis in `arms/haiku.py`'s
module docstring applies identically -- prompts are the same ~900-1,000
cacheable-prefix length, still below the 4,096-token cache minimum).
"""

from __future__ import annotations

import time

import anthropic

import harness.env  # noqa: F401  -- loads .env (ANTHROPIC_API_KEY) before client init
from arms.base import Arm, Prediction
from arms.haiku import _build_tool, _build_user_message
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "claude-sonnet-5"
PRICING_KEY = "claude-sonnet-5"
MAX_TOKENS = 200

TOOL_NAME = "choose_folder"

SYSTEM_PROMPT = (
    "You are a document sorting assistant. You will be given a rubric describing "
    "folders and the rules for assigning a document to one of them, followed by the "
    "document's content. Read the rubric carefully -- it is the only source of truth "
    "for how to sort, including any thresholds, exceptions, or lookups it states. "
    "Call the choose_folder tool exactly once with the single best-matching folder "
    "and your confidence in that choice."
)


class SonnetArm(Arm):
    name = "sonnet"

    def __init__(self, model: str = MODEL, spend_source: str = "sonnet_arm"):
        self._client = anthropic.Anthropic()
        self._model = model
        self._spend_source = spend_source

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        tool = _build_tool(rubric.folders)
        user_message = _build_user_message(doc_text, rubric)

        start = time.perf_counter()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool],
            tool_choice={"type": "tool", "name": TOOL_NAME},
        )
        latency_ms = (time.perf_counter() - start) * 1000

        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        folder_id = tool_use_block.input["folder_id"]
        confidence = float(tool_use_block.input["confidence"])

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cache_creation_tokens = response.usage.cache_creation_input_tokens or 0
        cache_read_tokens = response.usage.cache_read_input_tokens or 0

        record_spend(
            source=self._spend_source,
            model=PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            note=f"clause_type={rubric.clause_type} condition={rubric.condition}",
        )

        return Prediction(
            folder=folder_id,
            probabilities={},  # Sonnet's tool-use output has no probability distribution
            confidence=confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SonnetArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
