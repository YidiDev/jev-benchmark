"""emb-bge arm: BAAI/bge-m3 embedding cosine similarity against folder label
text -- the "stronger traditional baseline" from test-plan.md §3 (cited
there at 0.722 vs NLI's 0.579 on Banking77 in the published harness
zhuyansen/jev-zeroshot-vs-bert).

Like nli-bart, this arm only ever embeds the folder *display name*, never
the rubric criteria/instructions -- embeddings have no mechanism to consume
a rubric either. Same expectation as nli-bart: competitive on Condition A,
collapses on B/C.

`probabilities` here is a softmax (temperature=1, no tuning) over raw cosine
similarities, for reporting/confidence-at-errors only. Per test-plan.md §6,
calibration (ECE) is only computed for jev/openjev/haiku, not this arm, so
no claim is made that these softmax values are well-calibrated.
"""

from __future__ import annotations

import time

import numpy as np
from sentence_transformers import SentenceTransformer

from arms.base import Arm, Prediction
from rubrics.clauses import Rubric

MODEL_ID = "BAAI/bge-m3"


class EmbBgeArm(Arm):
    name = "emb-bge"

    def __init__(self, device: str | None = None):
        self._model = SentenceTransformer(MODEL_ID, device=device)
        self._label_cache: dict[tuple[str, ...], np.ndarray] = {}

    def _label_embeddings(self, folders: list[str]) -> np.ndarray:
        key = tuple(folders)
        if key not in self._label_cache:
            self._label_cache[key] = self._model.encode(list(folders), normalize_embeddings=True)
        return self._label_cache[key]

    def predict(self, doc_text: str, rubric: Rubric) -> Prediction:
        start = time.perf_counter()
        doc_emb = self._model.encode([doc_text], normalize_embeddings=True)[0]
        label_embs = self._label_embeddings(rubric.folders)
        sims = label_embs @ doc_emb  # cosine similarity: both sides L2-normalized
        latency_ms = (time.perf_counter() - start) * 1000

        exp = np.exp(sims - sims.max())
        probs = exp / exp.sum()

        best_idx = int(np.argmax(sims))
        probabilities = {f: float(p) for f, p in zip(rubric.folders, probs)}
        return Prediction(
            folder=rubric.folders[best_idx],
            probabilities=probabilities,
            confidence=float(probs[best_idx]),
            latency_ms=latency_ms,
        )
