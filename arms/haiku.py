"""haiku arm -- the reference ceiling that decides client adoption
(test-plan.md's Part 2). Claude Haiku 4.5, forced tool-use for constrained
`{folder_id, confidence}` output, same rubric decomposition as every other
arm: one question per document, full rubric text, no extra scaffolding or
multi-pass prompting that Jev doesn't also get (§5.2 equal-effort budget).

**Deviation from test-plan.md's "temp 0":** the live Messages API for this
account has no `temperature` parameter at all (confirmed via the SDK's
`Messages.create` signature and `platform.claude.com/docs/en/api/messages`
on 2026-09-21) -- it's been superseded by `output_config.effort`
(low/medium/high/xhigh/max), which controls reasoning depth, not sampling
randomness. There is therefore no lower-variance mode to opt into; every
call runs at whatever the API's default sampling behavior is. This makes
test-plan.md's run-to-run variance requirement (3 repeats, "including Haiku
at temp 0 which is still non-deterministic") even more load-bearing than
originally written: it was already the a priori expectation that Haiku
would show measurable run-to-run disagreement, and now that's the *only*
axis of variance available, not a residual one. Documented in
methodology.md §11.

Forced tool-use (rather than "ask for JSON in prose and regex it out") is
used specifically so a malformed/refused response is a hard API-level
failure surfaced immediately, not a silent parsing failure that could bias
results -- and so the `folder_id` is drawn from an explicit enum matching
`rubric.folders` exactly, structurally guaranteeing Haiku can't answer with
a folder that doesn't exist (mirroring Jev's `Choice` primitive, which has
the same guarantee built in).

**Prompt caching was evaluated and found ineffective for this model.**
A pre-flight cost projection showed the naive full 3-repeat, 4-condition run
would cost roughly $4.35 against the ~$3.93 remaining Anthropic budget, so
prompt caching (cache the rubric-dependent system/tool content, shared
across 60 docs x REPEATS=3 = up to 180 calls per (clause_type, condition)
pair) was tried as a fix. It didn't work: **Claude Haiku 4.5's minimum
cacheable prompt length is 4,096 tokens**
(platform.claude.com/docs/en/build-with-claude/prompt-caching#cache-limitations,
confirmed 2026-09-21) -- far above this arm's ~900-1,000-token cacheable
prefix (system prompt + rubric text + tool schema), so
`cache_creation_input_tokens`/`cache_read_input_tokens` came back 0 on every
real test call. Padding the prefix with ~3,000 tokens of meaningless filler
to clear the threshold was considered and rejected: it would only save
roughly $1.30, while injecting a large irrelevant preamble into a "fair
fight" reference arm's context is a bigger fairness/realism cost than that
savings is worth. `harness/spend_ledger.py` and `arms/base.Prediction` still
carry cache-aware fields (`cache_creation_tokens`/`cache_read_tokens`,
correctly priced per platform.claude.com's cache-write/cache-read
multipliers) in case a future arm or model can actually clear its cache
minimum -- they are simply always 0 here.

**Actual budget fix: REPEATS=2 for this arm instead of 3** (test-plan.md
specifies 3). Deliberate, documented scope reduction, not silent: all 4
conditions (A/B/C/SHUFFLE) and both splits are preserved in full -- what's
reduced is the third repeat used for the run-to-run variance metric, the
one secondary metric this cut affects. 2 repeats still yields a genuine
disagreement signal (test-plan.md's Haiku-is-non-deterministic expectation
holds at n=2 as well as n=3, just with less statistical power), and this
preserves the two metrics decision-relevant to the Part 2 adoption question
(per-condition accuracy, shuffle-control tracking) at full strength. See
methodology.md §11 for the full cost accounting and this decision's
rationale.
"""

from __future__ import annotations

import time

import anthropic

import harness.env  # noqa: F401  -- loads .env (ANTHROPIC_API_KEY) before client init
from arms.base import Arm, Prediction
from harness.spend_ledger import record_spend
from rubrics.clauses import Rubric

MODEL = "claude-haiku-4-5-20251001"
PRICING_KEY = "claude-haiku-4-5"
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


def _build_tool(folders: list[str]) -> dict:
    return {
        "name": TOOL_NAME,
        "description": "Record the chosen folder for this document.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "enum": folders,
                    "description": "The single folder this document belongs in.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence in this choice, from 0 (guessing) to 1 (certain).",
                },
            },
            "required": ["folder_id", "confidence"],
        },
    }


def _build_user_message(doc_text: str, rubric: Rubric) -> str:
    criteria_lines = "\n".join(f"- `{folder}`: {rubric.criteria[folder]}" for folder in rubric.folders)
    return (
        f"Rubric:\n{rubric.instructions}\n\n"
        f"Folder descriptions:\n{criteria_lines}\n\n"
        f"Document:\n{doc_text}"
    )


class HaikuArm(Arm):
    name = "haiku"

    def __init__(self, model: str = MODEL, spend_source: str = "haiku_arm"):
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
        # Always 0 -- caching doesn't clear Haiku 4.5's minimum, see module
        # docstring -- kept for schema uniformity with harness/spend_ledger.py.
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
            probabilities={},  # Haiku's tool-use output has no probability distribution
            confidence=confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HaikuArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
