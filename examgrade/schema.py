"""Structured metadata for one CT10 student's exam. Pydantic model
mirroring corpus/schema.py's DocumentMetadata and qtree/schema.py's
FormMetadata pattern, but for graded exams instead of documents/forms."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StudentMetadata(BaseModel):
    student_id: str

    # Latent ability parameter (0-1), Beta(2,2)-distributed -- never shown
    # to any grading arm, purely the generative mechanism behind scores.
    ability: float

    # True score per question, {question_id: int in [0, question.points]}.
    # This is the sole ground truth -- never derived from generated prose.
    scores: dict[str, int] = Field(default_factory=dict)

    total_true_score: int = 0  # sum(scores.values()), out of 100

    seed_trace: dict = Field(default_factory=dict)
