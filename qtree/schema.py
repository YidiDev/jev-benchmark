"""Structured metadata for one CT9 form. Pydantic model mirroring
corpus/schema.py's DocumentMetadata pattern, but for questionnaire forms
instead of documents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FormMetadata(BaseModel):
    form_id: str
    split: Literal["validation", "test"]

    # Full structured answers: {"standard": {qid: value}, "special": {qid: {content_correct, length_compliant}}}
    answers: dict = Field(default_factory=dict)

    # Ground truth, precomputed at generation time for convenience (also
    # independently recomputable from `answers` alone via qtree.tree.true_folder).
    true_folder: str = ""

    seed_trace: dict = Field(default_factory=dict)
