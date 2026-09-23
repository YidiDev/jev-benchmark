"""CT10 grading arms: Jev, Haiku, OpenJev, each supporting both chained
(one call per question) and whole-exam (one call, all 30 questions)
grading modes, at both with-key and without-key rubric conditions.

Jev/OpenJev use the Score primitive (points+1 ordered levels = "N of
`points` criteria satisfied") -- the first use of Score anywhere in this
benchmark. Whole-exam mode for Jev/OpenJev is a single system_one call
with 30 separate Score questions (Jev's documented multi-question-per-call
capability), state = the student's full exam transcript. Haiku has no
equivalent multi-question primitive, so whole-exam mode uses a single
forced tool call with one integer property per question (0..points each),
built dynamically to match every question's point range.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from typesafe_sdk import Score, TypeSafeClient

import harness.env  # noqa: F401 -- loads .env before any client init
from harness.spend_ledger import record_spend
from examgrade.questions import EXAM_QUESTIONS, ExamQuestion
from examgrade.rubric_text import question_rubric_text, score_level_descriptions

CHAINED_INSTRUCTIONS_PREFIX = (
    "Below is one student's answer to a single AP World History exam question, followed by the "
    "grading rubric for that question. Grade the answer strictly according to the rubric."
)
WHOLE_EXAM_INSTRUCTIONS_PREFIX = (
    "Below is a student's complete AP World History exam (30 questions and answers), followed by "
    "the grading rubric for every question. Grade every answer strictly according to its rubric."
)


@dataclass
class QuestionGrade:
    question_id: str
    score: int
    confidence: Optional[float] = None


@dataclass
class GradingResult:
    grades: dict[str, QuestionGrade] = field(default_factory=dict)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class _TypeSafeGradingArm:
    """Shared implementation for Jev and OpenJev -- identical except for
    base_url/api_key/model, matching every other Jev/OpenJev arm pair in
    this benchmark."""

    def __init__(self, client: TypeSafeClient, pricing_key: str, spend_source: str):
        self._client = client
        self._pricing_key = pricing_key
        self._spend_source = spend_source

    def grade_question(self, answer_text: str, question: ExamQuestion, with_key: bool) -> GradingResult:
        instructions = f"{CHAINED_INSTRUCTIONS_PREFIX}\n\n{question_rubric_text(question, with_key)}"
        levels = score_level_descriptions(question.points)
        question_obj = Score(instructions=instructions, criteria=levels)

        start = time.perf_counter()
        response = self._client.system_one(state=answer_text, questions={question.id: question_obj})
        latency_ms = (time.perf_counter() - start) * 1000

        answer = response.scores[question.id]
        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model=self._pricing_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"chained grade {question.id} with_key={with_key}",
        )

        score = round(answer.score)
        return GradingResult(
            grades={question.id: QuestionGrade(question.id, score, answer.confidence)},
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def grade_exam(self, full_exam_text: str, with_key: bool) -> GradingResult:
        questions = {}
        for q in EXAM_QUESTIONS:
            instructions = f"{WHOLE_EXAM_INSTRUCTIONS_PREFIX}\n\n{question_rubric_text(q, with_key)}"
            questions[q.id] = Score(instructions=instructions, criteria=score_level_descriptions(q.points))

        start = time.perf_counter()
        response = self._client.system_one(state=full_exam_text, questions=questions)
        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        record_spend(
            source=self._spend_source,
            model=self._pricing_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"whole-exam grade with_key={with_key}",
        )

        grades = {}
        for q in EXAM_QUESTIONS:
            ans = response.scores[q.id]
            grades[q.id] = QuestionGrade(q.id, round(ans.score), ans.confidence)

        return GradingResult(
            grades=grades,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class JevExamArm(_TypeSafeGradingArm):
    name = "jev"

    def __init__(self, model: str = "jev-latest", spend_source: str = "jev_arm_ct10"):
        super().__init__(TypeSafeClient(model=model), pricing_key="jev-latest", spend_source=spend_source)


class OpenJevExamArm(_TypeSafeGradingArm):
    name = "openjev"

    def __init__(self, model: str = "openjev-latest", spend_source: str = "openjev_arm_ct10"):
        client = TypeSafeClient(
            model=model,
            base_url=os.environ["CODIV_BASE_URL"],
            api_key=os.environ["CODIV_API_KEY"],
        )
        super().__init__(client, pricing_key="openjev", spend_source=spend_source)


class HaikuExamArm:
    name = "haiku"

    MODEL = "claude-haiku-4-5-20251001"
    PRICING_KEY = "claude-haiku-4-5"
    CHAINED_MAX_TOKENS = 200
    WHOLE_EXAM_MAX_TOKENS = 3000
    CHAINED_TOOL_NAME = "grade_answer"
    WHOLE_EXAM_TOOL_NAME = "grade_exam"

    SYSTEM_PROMPT_CHAINED = (
        "You are an AP World History exam grader. You will be given a student's answer to one "
        "question, followed by the grading rubric for that question. Grade strictly according to "
        "the rubric and call the grade_answer tool exactly once with the score and your confidence."
    )
    SYSTEM_PROMPT_WHOLE_EXAM = (
        "You are an AP World History exam grader. You will be given a student's complete 30-question "
        "exam, followed by the grading rubric for every question. Grade every answer strictly "
        "according to its own rubric and call the grade_exam tool exactly once with every question's "
        "score."
    )

    def __init__(self, model: str | None = None, spend_source: str = "haiku_arm_ct10"):
        self._client = anthropic.Anthropic()
        self._model = model or self.MODEL
        self._spend_source = spend_source

    def _chained_tool(self, points: int) -> dict:
        return {
            "name": self.CHAINED_TOOL_NAME,
            "description": "Record the score for this answer.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": points, "description": f"Score, 0-{points}."},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["score", "confidence"],
            },
        }

    def _whole_exam_tool(self) -> dict:
        properties = {}
        required = []
        for q in EXAM_QUESTIONS:
            properties[q.id] = {
                "type": "integer",
                "minimum": 0,
                "maximum": q.points,
                "description": f"Score for {q.id}, 0-{q.points}.",
            }
            required.append(q.id)
        return {
            "name": self.WHOLE_EXAM_TOOL_NAME,
            "description": "Record the score for every question on this exam.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "scores": {"type": "object", "properties": properties, "required": required},
                },
                "required": ["scores"],
            },
        }

    def grade_question(self, answer_text: str, question: ExamQuestion, with_key: bool) -> GradingResult:
        rubric = question_rubric_text(question, with_key)
        user_message = f"Student's answer:\n{answer_text}\n\nRubric:\n{rubric}"
        tool = self._chained_tool(question.points)

        start = time.perf_counter()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self.CHAINED_MAX_TOKENS,
            system=self.SYSTEM_PROMPT_CHAINED,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool],
            tool_choice={"type": "tool", "name": self.CHAINED_TOOL_NAME},
        )
        latency_ms = (time.perf_counter() - start) * 1000

        block = next(b for b in response.content if b.type == "tool_use")
        score = int(block.input["score"])
        confidence = float(block.input["confidence"])

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        record_spend(
            source=self._spend_source,
            model=self.PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"chained grade {question.id} with_key={with_key}",
        )

        return GradingResult(
            grades={question.id: QuestionGrade(question.id, score, confidence)},
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def grade_exam(self, full_exam_text: str, with_key: bool) -> GradingResult:
        rubric = "\n\n".join(question_rubric_text(q, with_key) for q in EXAM_QUESTIONS)
        user_message = f"Student's exam:\n{full_exam_text}\n\nRubric (all questions):\n{rubric}"
        tool = self._whole_exam_tool()

        start = time.perf_counter()
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self.WHOLE_EXAM_MAX_TOKENS,
            system=self.SYSTEM_PROMPT_WHOLE_EXAM,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool],
            tool_choice={"type": "tool", "name": self.WHOLE_EXAM_TOOL_NAME},
        )
        latency_ms = (time.perf_counter() - start) * 1000

        block = next(b for b in response.content if b.type == "tool_use")
        scores = block.input["scores"]

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        record_spend(
            source=self._spend_source,
            model=self.PRICING_KEY,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            note=f"whole-exam grade with_key={with_key}",
        )

        grades = {q.id: QuestionGrade(q.id, int(scores[q.id]), None) for q in EXAM_QUESTIONS}
        return GradingResult(
            grades=grades,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HaikuExamArm":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class SonnetExamArm(HaikuExamArm):
    """Sonnet 5's CT10 exam-grading arm -- see `arms/sonnet.py` module
    docstring for why this arm exists (Part 2's declined-then-revisited
    Sonnet comparison, motivated specifically by CT10 whole-exam mode being
    where Haiku underperformed Jev most).

    All behavior inherited from `HaikuExamArm` unchanged (constants read via
    `self.X` throughout, both `grade_question`/chained and `grade_exam`/
    whole-exam modes) -- override-only subclass, identical prompts/tool
    schemas, only the model differs.
    """

    name = "sonnet"

    MODEL = "claude-sonnet-5"
    PRICING_KEY = "claude-sonnet-5"

    def __init__(self, model: str | None = None, spend_source: str = "sonnet_arm_ct10"):
        super().__init__(model=model, spend_source=spend_source)

    def __enter__(self) -> "SonnetExamArm":
        return self
