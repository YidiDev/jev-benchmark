"""CT9 chunked-execution arms: Jev and Haiku, adapted for the "choose among
k-step destinations, given the form transcript + subtree description"
primitive instead of CT1-8's "choose a folder for a document" primitive.

Same decomposition discipline as arms/jev.py and arms/haiku.py: state is
the form's 30-Q&A transcript (the "document"), instructions is the subtree
description built by qtree/subtree.py (the "rubric" for this specific
chunk), criteria/options are the k-step destination ids. Every call is
logged through harness.spend_ledger.record_spend, same as every other paid
call in this benchmark.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from typesafe_sdk import Choice, TypeSafeClient

import harness.env  # noqa: F401 -- loads .env before any client init
from harness.spend_ledger import record_spend

CHUNK_INSTRUCTIONS_PREFIX = (
    "Below is a completed screening form (30 questions and free-text answers), followed by a "
    "piece of internal decision logic. Read the form's answers carefully, then trace the decision "
    "logic to determine the correct destination, exactly as instructed."
)


@dataclass
class ChunkPrediction:
    chosen: str
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: Optional[float] = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class JevChunkArm:
    name = "jev"

    def __init__(self, model: str = "jev-latest", spend_source: str = "jev_arm_ct9"):
        self._client = TypeSafeClient(model=model)
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = Choice(
            instructions=f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            criteria=criteria,
        )

        start = time.perf_counter()
        response = self._client.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["destination"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model="jev-latest",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JevChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class OpenJevChunkArm:
    """Same as JevChunkArm, pointed at the free-hosted Codiv endpoint
    (see arms/openjev.py's module docstring for the full rationale)."""

    name = "openjev"

    def __init__(self, model: str = "openjev-latest", spend_source: str = "openjev_arm_ct9"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["CODIV_BASE_URL"],
            api_key=os.environ["CODIV_API_KEY"],
        )
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = Choice(
            instructions=f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            criteria=criteria,
        )

        start = time.perf_counter()
        response = self._client.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["destination"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model="openjev",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenJevChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class HaikuChunkArm:
    name = "haiku"

    MODEL = "claude-haiku-4-5-20251001"
    PRICING_KEY = "claude-haiku-4-5"
    MAX_TOKENS = 200
    TOOL_NAME = "choose_destination"

    SYSTEM_PROMPT = (
        "You are a decision-logic execution assistant. You will be given a completed screening "
        "form (30 questions and answers), followed by a piece of internal decision logic "
        "describing one or more decision positions, the question asked at each, and where each "
        "possible answer leads. Read the form's answers, trace through the logic exactly as "
        "stated, and call the choose_destination tool exactly once with the single position you "
        "land on and your confidence in that choice."
    )

    def __init__(self, model: str | None = None, spend_source: str = "haiku_arm_ct9"):
        self._client = anthropic.Anthropic()
        self._model = model or self.MODEL
        self._spend_source = spend_source

    def _build_tool(self, destinations: list[str]) -> dict:
        return {
            "name": self.TOOL_NAME,
            "description": "Record the destination position reached after tracing the decision logic.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "enum": destinations,
                        "description": "The single position reached after tracing the logic.",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence in this choice, from 0 (guessing) to 1 (certain).",
                    },
                },
                "required": ["destination", "confidence"],
            },
        }

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        tool = self._build_tool(destinations)
        user_message = f"Form:\n{form_text}\n\nDecision logic:\n{subtree_description}"

        start = time.perf_counter()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self.MAX_TOKENS,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool],
            tool_choice={"type": "tool", "name": self.TOOL_NAME},
        )
        latency_ms = (time.perf_counter() - start) * 1000

        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        chosen = tool_use_block.input["destination"]
        confidence = float(tool_use_block.input["confidence"])

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        record_spend(
            source=self._spend_source,
            model=self.PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=chosen,
            probabilities={},
            confidence=confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HaikuChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class LayaChunkArm:
    """Laya's CT9 chunk arm -- same in-process convaiinnovations/laya agent
    as arms/laya.py, adapted to the "choose among k-step destinations"
    primitive. Laya's own 512-token max_len (see arms/laya.py's docstring)
    is the interesting constraint here: at k=1 the subtree description is
    short, but at k=10 the combined form-transcript + subtree-description
    text is large enough that Laya's own tokenizer-level truncation (inside
    `build_sequence`) may cut into either the form or the destination
    descriptions -- unlike CT1-8, no separate long-context clause type
    exists for CT9, so this is read directly off the k=1 vs k=10 comparison.
    """

    name = "laya"

    def __init__(self, model_id: str = "convaiinnovations/laya", spend_source: str = "laya_arm_ct9"):
        from laya import load

        self._agent = load(model_id, device="cpu")
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = {
            "type": "choice",
            "instructions": f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            "criteria": criteria,
        }

        start = time.perf_counter()
        response = self._agent.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response["answers"]["destination"]
        usage = response["usage"]
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]

        record_spend(
            source=self._spend_source,
            model="laya",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer["choice"],
            probabilities=dict(answer["probabilities"]),
            confidence=answer["confidence"],
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


class KevChunkArm:
    """Same as JevChunkArm, pointed at a self-hosted kev.serve instance --
    see arms/kev.py's module docstring for the full rationale."""

    name = "kev"

    def __init__(self, model: str = "kev-latest", spend_source: str = "kev_arm_ct9"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["KEV_BASE_URL"],
            api_key=os.environ.get("KEV_API_KEY") or "local",
        )
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = Choice(
            instructions=f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            criteria=criteria,
        )

        start = time.perf_counter()
        response = self._client.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["destination"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model="kev-4b",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "KevChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class NimbleChunkArm:
    """Same shape as KevChunkArm, pointed at the custom FastAPI wrapper
    around Nimble's CudaCandidateScorer -- see arms/nimble.py and
    scripts/serving/nimble_server.py.

    CT9 is exactly the shape Nimble's own architecture is *not* specialized
    for (unlike CLM's cached action embeddings) -- Nimble scores each
    field/candidate from scratch per call with no cross-call caching, so
    this arm exists purely as the accuracy comparison point, not a speed
    claim.
    """

    name = "nimble"

    def __init__(self, model: str = "nimble-latest", spend_source: str = "nimble_arm_ct9"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["NIMBLE_BASE_URL"],
            api_key=os.environ.get("NIMBLE_API_KEY") or "local",
        )
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = Choice(
            instructions=f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            criteria=criteria,
        )

        start = time.perf_counter()
        response = self._client.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["destination"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model="nimble-9b",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NimbleChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class CLMChunkArm:
    """CT9-only arm (see methodology.md §18): `Contrastive-LM/CLM-v0.1-8B`,
    a dual-encoder (state + action) contrastive model that scores each
    candidate destination by dot-product similarity to the state embedding,
    served via `clm-serve`'s real TypeSafe-compatible `/v1/systemone` on top
    of a vLLM Qwen3-8B pooling backend (self-hosted on the same rented GPU
    as Kev-4B/Nimble-9B -- see scripts/serving/clm_setup.sh).

    This arm exists to test an architecture hypothesis, not a scaling one:
    OpenJev collapses on CT9 (see qtree/scoring.py's OpenJev results); CLM's
    action-cache mechanism (`--action-cache`, enabled by scripts/serving/
    clm_setup.sh) means a destination's action embedding is computed once
    and reused across every state that reaches it, which is architecturally
    suited to CT9's shape (destinations repeat across the tree). If CLM
    doesn't collapse the way OpenJev did, that is evidence for "the shape of
    caching matters for tree traversal," not "8B beats 26B-A4B."

    CLM's default 2,048-token serving limit is raised to 8,192 for this
    corpus (`vllm serve ... --max-model-len 8192` + `clm-serve --max-tokens
    8192`, see clm_setup.sh) since CT9's k=10 combined form + subtree text
    can run to ~3,100 tokens, above the 2,048 default.
    """

    name = "clm"

    def __init__(self, model: str = "clm-latest", spend_source: str = "clm_arm_ct9"):
        self._client = TypeSafeClient(
            model=model,
            base_url=os.environ["CLM_BASE_URL"],
            api_key=os.environ.get("CLM_API_KEY") or "local",
        )
        self._spend_source = spend_source

    def predict_chunk(self, form_text: str, subtree_description: str, destinations: list[str]) -> ChunkPrediction:
        criteria = {d: f"Trace the decision logic and land on `{d}`." for d in destinations}
        question = Choice(
            instructions=f"{CHUNK_INSTRUCTIONS_PREFIX}\n\n{subtree_description}",
            criteria=criteria,
        )

        start = time.perf_counter()
        response = self._client.system_one(state=form_text, questions={"destination": question})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.choices["destination"]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model="clm-8b",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note="ct9 chunk",
        )

        return ChunkPrediction(
            chosen=answer.choice,
            probabilities=dict(answer.probabilities),
            confidence=answer.confidence,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CLMChunkArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class SonnetChunkArm(HaikuChunkArm):
    """Sonnet 5's CT9 chunk arm -- see `arms/sonnet.py` module docstring for why
    this arm exists (Part 2's declined-then-revisited Sonnet comparison).

    All behavior inherited from `HaikuChunkArm` unchanged (constants are read
    via `self.X` throughout that class, so this override-only subclass is
    exactly identical in prompt shape, tool schema, and chaining behavior --
    the only difference is which model answers).
    """

    name = "sonnet"

    MODEL = "claude-sonnet-5"
    PRICING_KEY = "claude-sonnet-5"

    def __init__(self, model: str | None = None, spend_source: str = "sonnet_arm_ct9"):
        super().__init__(model=model, spend_source=spend_source)

    def __enter__(self) -> "SonnetChunkArm":
        return self
