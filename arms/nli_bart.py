"""nli-bart arm: facebook/bart-large-mnli zero-shot classification.

This is an *instrument*, not a fair-fight baseline (test-plan.md §3): the HF
zero-shot-classification pipeline can only score each candidate label's
*display text* against the document via NLI entailment -- it never sees
rubric criteria or instructions, because the whole point of the pipeline is
that it has no other way to consume a rubric. That is exactly the property
being measured: whether Jev is doing something more than "match label text
to document content." Expect this arm to do fine on Condition A (semantic
folder names carry real signal), and to collapse toward chance on Condition
B (opaque ids carry no signal) and Condition C (misleading names actively
point away from the correct answer).
"""

from __future__ import annotations

import time

from transformers import pipeline

from arms.base import Arm, Prediction
from rubrics.clauses import Rubric

MODEL_ID = "facebook/bart-large-mnli"
HYPOTHESIS_TEMPLATE = "This document should be filed in the folder called {}."


def _default_device() -> int:
    import torch

    return 0 if torch.cuda.is_available() else -1


class NliBartArm(Arm):
    name = "nli-bart"

    def __init__(self, device: int | str | None = None):
        self._pipe = pipeline(
            "zero-shot-classification",
            model=MODEL_ID,
            device=device if device is not None else _default_device(),
        )

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        start = time.perf_counter()
        result = self._pipe(
            doc_text,
            candidate_labels=rubric.folders,
            hypothesis_template=HYPOTHESIS_TEMPLATE,
            multi_label=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        probabilities = dict(zip(result["labels"], result["scores"]))
        return Prediction(
            folder=result["labels"][0],
            probabilities=probabilities,
            confidence=result["scores"][0],
            latency_ms=latency_ms,
        )
