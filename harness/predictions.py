"""Shared prediction record format, written by every arm's runner so
harness/scoring.py can score all five arms uniformly.

One JSONL file per arm at results/predictions/{arm}.jsonl. Condition
"SHUFFLE" is deliberately never written here -- the shuffle control (§5.1)
reuses each arm's Condition B records unchanged (same opaque-id folder set is
shown to the model either way; only the scoring-time answer key differs), so
scoring.py must synthesize shuffle-control accuracy from condition="B" rows
via rubrics.ground_truth.correct_folder(..., shuffle=True).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PREDICTIONS_DIR = Path(__file__).resolve().parent.parent / "results" / "predictions"


@dataclass
class PredictionRecord:
    arm: str
    doc_id: str
    clause_type: int
    condition: str  # "A" | "B" | "C" -- never "SHUFFLE", see module docstring
    split: str  # "validation" | "test"
    repeat: int  # 1 for deterministic local arms; 1..REPEATS for stochastic API arms
    predicted_folder: str
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


def path_for(arm: str) -> Path:
    return PREDICTIONS_DIR / f"{arm}.jsonl"


def append_prediction(record: PredictionRecord) -> None:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    with path_for(record.arm).open("a") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def load_predictions(arm: str) -> list[PredictionRecord]:
    p = path_for(arm)
    if not p.exists():
        return []
    rows = []
    with p.open() as f:
        for line in f:
            if line.strip():
                rows.append(PredictionRecord(**json.loads(line)))
    return rows


def existing_keys(arm: str) -> set[tuple[str, str, int]]:
    """(doc_id, condition, repeat) keys already recorded -- lets runners
    resume after an interruption without re-predicting or double-billing."""
    return {(r.doc_id, r.condition, r.repeat) for r in load_predictions(arm)}
