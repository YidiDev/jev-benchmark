"""Orchestrates CT9's chunked traversal: for each form x k-value x repeat
(x labeling scheme, opaque/semantic, only at k=10), walks the tree in
10/k chunks with real compounding -- each chunk after the first starts
from wherever the *model's own* previous chunk answer actually landed, not
from the ground-truth-correct position. See qtree/subtree.py for how each
chunk's decision logic is described, and methodology.md §13 for the full
design rationale.

Resumable: a trace's progress is reconstructed from whatever chunks are
already on disk for its (form_id, k, repeat, labeling) key, so an
interrupted run picks back up from its last completed chunk rather than
re-walking (and re-billing) the whole trace.

Usage:
    python -m qtree.runner --arm jev
    python -m qtree.runner --arm jev --limit 2 --repeats 1 --k 10   # debug
    python -m qtree.runner --arm haiku --k 10                       # one k value only
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from harness.constants import REPEATS
from harness.spend_ledger import BudgetExceeded
from qtree.generate_metadata import load_manifest
from qtree.predictions import ChunkRecord, append_chunk, existing_trace_progress
from qtree.subtree import describe_subtree, folder_display_mapping
from qtree.tree import ROOT_ID, walk

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
K_VALUES = (1, 2, 5, 10)


def _form_text(form_id: str) -> str:
    return (DOCUMENTS_DIR / f"{form_id}.txt").read_text()


def _build_arm(name: str):
    if name == "jev":
        from qtree.arms import JevChunkArm

        return JevChunkArm()
    if name == "haiku":
        from qtree.arms import HaikuChunkArm

        return HaikuChunkArm()
    raise ValueError(f"unknown CT9 arm {name!r}")


def _resolve_canonical(chosen_display: str, folder_display: dict[str, str]) -> str:
    reverse = {v: k for k, v in folder_display.items()}
    return reverse.get(chosen_display, chosen_display)


def run(
    arm_name: str,
    limit: int | None = None,
    repeats: int | None = None,
    k_values: tuple[int, ...] = K_VALUES,
    split: str | None = None,
) -> None:
    repeats = repeats or REPEATS
    print(f"[qtree/{arm_name}] initializing (repeats={repeats}, k={k_values})...")
    arm = _build_arm(arm_name)

    manifest = load_manifest()
    if split:
        manifest = [m for m in manifest if m.split == split]
    if limit:
        manifest = manifest[:limit]

    progress = existing_trace_progress(arm_name)

    n_traces_seen = 0
    n_traces_done_now = 0
    n_chunks_written = 0
    t0 = time.time()

    try:
        for metadata in manifest:
            form_text = _form_text(metadata.form_id)
            answers = metadata.answers
            for k in k_values:
                n_chunks_total = 10 // k
                labelings = ("semantic", "opaque") if k == 10 else ("semantic",)
                for labeling in labelings:
                    folder_display = folder_display_mapping(labeling)
                    for repeat in range(1, repeats + 1):
                        n_traces_seen += 1
                        key = (metadata.form_id, k, repeat, labeling)
                        existing = progress.get(key, [])
                        if len(existing) >= n_chunks_total:
                            continue

                        current = existing[-1].chosen_canonical if existing else ROOT_ID
                        for chunk_index in range(len(existing), n_chunks_total):
                            description, dest_display = describe_subtree(current, k, folder_display)
                            pred = arm.predict_chunk(form_text, description, dest_display)
                            chosen_canonical = _resolve_canonical(pred.chosen, folder_display)
                            true_local = walk(answers, start=current, steps=k)

                            record = ChunkRecord(
                                arm=arm_name,
                                form_id=metadata.form_id,
                                split=metadata.split,
                                k=k,
                                repeat=repeat,
                                labeling=labeling,
                                chunk_index=chunk_index,
                                start_node=current,
                                destinations=[_resolve_canonical(d, folder_display) for d in dest_display],
                                chosen_display=pred.chosen,
                                chosen_canonical=chosen_canonical,
                                true_local_destination=true_local,
                                local_correct=(chosen_canonical == true_local),
                                confidence=pred.confidence,
                                latency_ms=pred.latency_ms,
                                input_tokens=pred.input_tokens,
                                output_tokens=pred.output_tokens,
                            )
                            append_chunk(record)
                            progress.setdefault(key, []).append(record)
                            n_chunks_written += 1
                            current = chosen_canonical

                        n_traces_done_now += 1
                        if n_traces_seen % 20 == 0:
                            elapsed = time.time() - t0
                            print(
                                f"[qtree/{arm_name}] {n_traces_seen} traces seen, "
                                f"{n_traces_done_now} newly completed, {n_chunks_written} chunks "
                                f"written ({elapsed:.1f}s elapsed)"
                            )
    except BudgetExceeded as e:
        print(f"[qtree/{arm_name}] STOPPED (budget): {e}")
        raise
    finally:
        if hasattr(arm, "close"):
            arm.close()

    elapsed = time.time() - t0
    print(
        f"[qtree/{arm_name}] done: {n_traces_seen} traces seen, {n_traces_done_now} newly "
        f"completed, {n_chunks_written} chunks written in {elapsed:.1f}s"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=["jev", "haiku"])
    parser.add_argument("--limit", type=int, default=None, help="limit to first N manifest rows (debug)")
    parser.add_argument("--repeats", type=int, default=None, help="override REPEATS (debug)")
    parser.add_argument("--k", type=int, nargs="+", default=None, help="restrict to specific k values, e.g. --k 10")
    parser.add_argument("--split", choices=["validation", "test"], default=None)
    args = parser.parse_args()
    k_values = tuple(args.k) if args.k else K_VALUES
    run(args.arm, limit=args.limit, repeats=args.repeats, k_values=k_values, split=args.split)
