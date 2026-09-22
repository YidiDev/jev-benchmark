"""Scoring for CT9's chunked traversal: end-to-end accuracy by (arm, k,
labeling), per-chunk local accuracy (the "bad at individual steps" vs
"compounds" diagnostic), and the semantic-vs-opaque comparison at k=10.
"""

from __future__ import annotations

from collections import defaultdict

from harness.bootstrap import bootstrap_ci
from qtree.generate_metadata import load_manifest
from qtree.predictions import ChunkRecord, group_traces, load_chunks

ARMS = ("jev", "haiku", "openjev")
K_VALUES = (1, 2, 5, 10)


def _manifest_index() -> dict[str, str]:
    """form_id -> true_folder."""
    return {m.form_id: m.true_folder for m in load_manifest()}


def end_to_end_accuracy(arm: str) -> list[dict]:
    """Final-folder accuracy per (k, labeling), with bootstrap CI."""
    truth = _manifest_index()
    groups = group_traces(load_chunks(arm))
    buckets: dict[tuple[int, str], list[bool]] = defaultdict(list)
    for (form_id, k, _repeat, labeling), chunks in groups.items():
        final = chunks[-1].chosen_canonical
        correct = final == truth[form_id]
        buckets[(k, labeling)].append(correct)

    rows = []
    for (k, labeling), values in sorted(buckets.items()):
        n = len(values)
        c = sum(values)
        lo, hi = bootstrap_ci(values, purpose=f"qtree_bootstrap::{arm}::k{k}::{labeling}")
        rows.append({"arm": arm, "k": k, "labeling": labeling, "n": n, "correct": c, "accuracy": c / n, "ci_lo": lo, "ci_hi": hi})
    return rows


def local_step_accuracy(arm: str) -> list[dict]:
    """Per-chunk local accuracy by k -- "given wherever the model actually
    was, did it correctly execute this one chunk's logic." Distinguishes
    "bad at individual steps" from "fine locally, drifts and compounds."""
    chunks = load_chunks(arm)
    buckets: dict[int, list[bool]] = defaultdict(list)
    for c in chunks:
        buckets[c.k].append(c.local_correct)

    rows = []
    for k, values in sorted(buckets.items()):
        n = len(values)
        s = sum(values)
        lo, hi = bootstrap_ci(values, purpose=f"qtree_bootstrap_local::{arm}::k{k}")
        rows.append({"arm": arm, "k": k, "n": n, "correct": s, "accuracy": s / n, "ci_lo": lo, "ci_hi": hi})
    return rows


def all_local_correct_rate(arm: str) -> list[dict]:
    """Fraction of traces where EVERY chunk was locally correct -- if this
    is much higher than end-to-end accuracy, it's not that the model
    can't execute the local logic, it's that it can't hold its own
    reported position steady between calls (misreports where it "is")."""
    truth = _manifest_index()
    groups = group_traces(load_chunks(arm))
    buckets: dict[tuple[int, str], list[tuple[bool, bool]]] = defaultdict(list)
    for (form_id, k, _repeat, labeling), chunks in groups.items():
        final = chunks[-1].chosen_canonical
        end_to_end_correct = final == truth[form_id]
        all_correct = all(c.local_correct for c in chunks)
        buckets[(k, labeling)].append((all_correct, end_to_end_correct))

    rows = []
    for (k, labeling), pairs in sorted(buckets.items()):
        n = len(pairs)
        all_local = sum(1 for a, _ in pairs if a)
        e2e = sum(1 for _, e in pairs if e)
        # Traces where every chunk was locally correct but the final answer
        # was still wrong (or vice versa) -- the "drift without local error"
        # signature is only possible if end_to_end used a DIFFERENT true
        # answer path than what local-correctness checks (local correctness
        # is relative to wherever the model actually was, not the true root
        # path), so this is exactly the diagnostic test-plan called for.
        all_local_but_wrong = sum(1 for a, e in pairs if a and not e)
        rows.append(
            {
                "arm": arm,
                "k": k,
                "labeling": labeling,
                "n": n,
                "all_local_correct_rate": all_local / n,
                "end_to_end_accuracy": e2e / n,
                "all_local_correct_but_final_wrong": all_local_but_wrong,
            }
        )
    return rows


def confidence_at_local_errors(arm: str) -> dict:
    chunks = load_chunks(arm)
    errs = [c.confidence for c in chunks if not c.local_correct and c.confidence is not None]
    corr = [c.confidence for c in chunks if c.local_correct and c.confidence is not None]

    def stats(xs: list[float]) -> dict | None:
        if not xs:
            return None
        return {"n": len(xs), "mean": sum(xs) / len(xs)}

    return {"arm": arm, "at_local_errors": stats(errs), "at_local_correct": stats(corr)}


def disagreement_at_k10(arm: str, labeling: str = "semantic") -> dict:
    """Run-to-run disagreement at k=10 (single call, directly comparable to
    CT1-8's disagreement metric)."""
    groups = group_traces(load_chunks(arm))
    by_form: dict[str, set[str]] = defaultdict(set)
    for (form_id, k, _repeat, lbl), chunks in groups.items():
        if k == 10 and lbl == labeling:
            by_form[form_id].add(chunks[-1].chosen_canonical)
    total = len(by_form)
    disagreeing = sum(1 for preds in by_form.values() if len(preds) > 1)
    return {"arm": arm, "labeling": labeling, "total_forms": total, "disagreeing": disagreeing, "rate": disagreeing / total if total else 0.0}
