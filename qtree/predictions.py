"""Prediction storage for CT9's chunked traversal -- structurally
different from harness/predictions.py's one-record-per-document format,
since one (form, k, repeat, labeling) trace produces a *sequence* of
10/k chunk decisions with real compounding (chunk i+1 starts wherever
chunk i's own answer actually landed).

One JSONL file per arm at results/predictions/qtree_{arm}.jsonl. Each line
is one chunk. A full trace is reconstructed by grouping on
(form_id, k, repeat, labeling) and sorting by chunk_index; the final
folder is the last chunk's chosen_canonical.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PREDICTIONS_DIR = Path(__file__).resolve().parent.parent / "results" / "predictions"


@dataclass
class ChunkRecord:
    arm: str
    form_id: str
    split: str
    k: int
    repeat: int
    labeling: str  # "semantic" | "opaque" -- only varies at k=10, else always "semantic"
    chunk_index: int  # 0-based position within the trace
    start_node: str  # canonical node id this chunk started from
    destinations: list[str] = field(default_factory=list)  # canonical ids offered as choices this chunk
    chosen_display: str = ""  # what the model actually said (may be an opaque folder id)
    chosen_canonical: str = ""  # resolved back to a real node/folder id
    true_local_destination: str = ""  # ground-truth destination FROM start_node (not necessarily the globally-true path)
    local_correct: bool = False
    confidence: float | None = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


def path_for(arm: str) -> Path:
    return PREDICTIONS_DIR / f"qtree_{arm}.jsonl"


def append_chunk(record: ChunkRecord) -> None:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    with path_for(record.arm).open("a") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def load_chunks(arm: str) -> list[ChunkRecord]:
    p = path_for(arm)
    if not p.exists():
        return []
    rows = []
    with p.open() as f:
        for line in f:
            if line.strip():
                rows.append(ChunkRecord(**json.loads(line)))
    return rows


def group_traces(records: list[ChunkRecord]) -> dict[tuple[str, int, int, str], list[ChunkRecord]]:
    """Groups chunk records by (form_id, k, repeat, labeling), sorted by
    chunk_index within each group."""
    groups: dict[tuple[str, int, int, str], list[ChunkRecord]] = {}
    for r in records:
        key = (r.form_id, r.k, r.repeat, r.labeling)
        groups.setdefault(key, []).append(r)
    for key, chunks in groups.items():
        chunks.sort(key=lambda c: c.chunk_index)
    return groups


def existing_trace_progress(arm: str) -> dict[tuple[str, int, int, str], list[ChunkRecord]]:
    """Same as group_traces, over everything currently on disk for `arm` --
    used by the runner to figure out, per (form, k, repeat, labeling),
    how many chunks are already done and where the trace currently stands."""
    return group_traces(load_chunks(arm))
