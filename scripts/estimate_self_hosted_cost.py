"""Estimates what nli-bart, emb-bge, and a self-hosted OpenJev would cost to
run on rented GPU compute, instead of reporting a flat "$0.00" next to
Jev/Haiku/Sonnet's real API pricing.

This benchmark's real, metered spend for these three arms genuinely is
$0.00 -- nli-bart/emb-bge ran locally on this machine's own hardware, and
openjev ran on Codiv's free hosted tier. That is accurate and stays
unchanged in results/spend_ledger.jsonl and every "actual spend" number in
this repo. But "$0.00" is a misleading number to put in a cost *comparison*
against models that do cost money to run: if you deployed any of these
three for real, you'd pay for the compute somewhere. This script computes a
documented, auditable estimate of that cost -- see harness/constants.py's
SELF_HOSTED_PRICING block for the exact hardware/throughput assumptions per
model, and methodology.md §17 for the full writeup.

Token counts:
  - nli-bart / emb-bge: these arms never logged token counts during the
    real run (they call local model objects directly, not a metered API),
    so this script re-tokenizes the exact same input each arm actually
    processed -- doc text from corpus/documents/, rubric/folder text from
    rubrics.clauses.build_rubric() -- using each model's real HuggingFace
    tokenizer, matched row-for-row against results/predictions/{arm}.jsonl.
    No re-inference, no GPU needed, just re-deriving the token count the
    original run's input actually had.
  - openjev: input tokens were already logged for real (Codiv's endpoint
    reports them even on the free tier) in every results/predictions/
    {openjev,qtree_openjev,examgrade_openjev}.jsonl row -- summed directly,
    no re-tokenization needed. Output tokens are never logged (always 0),
    a real limitation noted in the output.

Usage: `python -m scripts.estimate_self_hosted_cost` (writes
results/self_hosted_cost_estimate.json).
"""

from __future__ import annotations

import json
from pathlib import Path

from transformers import AutoTokenizer

from harness.spend_ledger import estimated_self_hosted_cost
from rubrics.clauses import build_rubric

ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = ROOT / "corpus" / "documents"
PREDICTIONS_DIR = ROOT / "results" / "predictions"
OUT_PATH = ROOT / "results" / "self_hosted_cost_estimate.json"

HYPOTHESIS_TEMPLATE = "This document should be filed in the folder called {}."


def _doc_text(doc_id: str) -> str:
    return (DOCUMENTS_DIR / f"{doc_id}.txt").read_text()


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open() if line.strip()]


def _nli_bart_tokens() -> int:
    tok = AutoTokenizer.from_pretrained("facebook/bart-large-mnli")
    rows = _load_jsonl(PREDICTIONS_DIR / "nli-bart.jsonl")
    rubric_cache: dict[tuple[int, str], object] = {}
    total = 0
    for r in rows:
        key = (r["clause_type"], r["condition"])
        rubric = rubric_cache.setdefault(key, build_rubric(*key))
        text = _doc_text(r["doc_id"])
        for folder in rubric.folders:
            hyp = HYPOTHESIS_TEMPLATE.format(folder)
            total += len(tok(text, hyp, truncation=True, max_length=1024).input_ids)
    return total, len(rows)


def _emb_bge_tokens() -> int:
    tok = AutoTokenizer.from_pretrained("BAAI/bge-m3")
    rows = _load_jsonl(PREDICTIONS_DIR / "emb-bge.jsonl")
    rubric_cache: dict[tuple[int, str], object] = {}
    label_cache: set[tuple[str, ...]] = set()
    total = 0
    for r in rows:
        key = (r["clause_type"], r["condition"])
        rubric = rubric_cache.setdefault(key, build_rubric(*key))
        text = _doc_text(r["doc_id"])
        total += len(tok(text, truncation=True, max_length=8192).input_ids)
        fkey = tuple(rubric.folders)
        if fkey not in label_cache:  # matches arms/emb_bge.py's _label_embeddings cache
            label_cache.add(fkey)
            for f in rubric.folders:
                total += len(tok(f, truncation=True, max_length=8192).input_ids)
    return total, len(rows)


def _openjev_tokens_by_task() -> dict[str, tuple[int, int, int]]:
    """(input_tokens, output_tokens, n_rows) per task family, summed
    directly from already-logged real usage -- no re-tokenization."""
    files = {
        "ct1_8": PREDICTIONS_DIR / "openjev.jsonl",
        "ct9": PREDICTIONS_DIR / "qtree_openjev.jsonl",
        "ct10": PREDICTIONS_DIR / "examgrade_openjev.jsonl",
    }
    out = {}
    for task, path in files.items():
        rows = _load_jsonl(path)
        in_tok = sum(r.get("input_tokens", 0) for r in rows)
        out_tok = sum(r.get("output_tokens", 0) for r in rows)
        out[task] = (in_tok, out_tok, len(rows))
    return out


def main() -> None:
    nli_tokens, nli_n = _nli_bart_tokens()
    bge_tokens, bge_n = _emb_bge_tokens()
    openjev_by_task = _openjev_tokens_by_task()

    report: dict = {
        "note": (
            "Estimated self-hosted compute cost, NOT real metered spend. "
            "Real spend for these three arms is $0.00 (local hardware / free "
            "hosted tier) and stays that way in results/spend_ledger.jsonl. "
            "See harness/constants.py's SELF_HOSTED_PRICING and "
            "methodology.md §17 for the hardware/throughput assumptions "
            "behind every number below."
        ),
        "arms": {
            "nli-bart": {
                "task": "ct1_8",
                "n_rows": nli_n,
                "input_tokens": nli_tokens,
                "output_tokens": 0,
                "estimated_cost_usd": estimated_self_hosted_cost("nli-bart", nli_tokens, 0),
            },
            "emb-bge": {
                "task": "ct1_8",
                "n_rows": bge_n,
                "input_tokens": bge_tokens,
                "output_tokens": 0,
                "estimated_cost_usd": estimated_self_hosted_cost("emb-bge", bge_tokens, 0),
            },
            "openjev-self-hosted": {},
        },
    }

    openjev_total_cost = 0.0
    openjev_total_in = 0
    openjev_total_out = 0
    for task, (in_tok, out_tok, n_rows) in openjev_by_task.items():
        cost = estimated_self_hosted_cost("openjev-self-hosted", in_tok, out_tok)
        report["arms"]["openjev-self-hosted"][task] = {
            "n_rows": n_rows,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "estimated_cost_usd": cost,
        }
        openjev_total_cost += cost
        openjev_total_in += in_tok
        openjev_total_out += out_tok
    report["arms"]["openjev-self-hosted"]["total"] = {
        "input_tokens": openjev_total_in,
        "output_tokens": openjev_total_out,
        "estimated_cost_usd": openjev_total_cost,
    }

    OUT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT_PATH}")
    print(f"nli-bart:  {nli_tokens:>10,} input tok -> ${report['arms']['nli-bart']['estimated_cost_usd']:.4f}")
    print(f"emb-bge:   {bge_tokens:>10,} input tok -> ${report['arms']['emb-bge']['estimated_cost_usd']:.4f}")
    print(f"openjev:   {openjev_total_in:>10,} input tok -> ${openjev_total_cost:.4f} (self-hosted, all 3 task families)")


if __name__ == "__main__":
    main()
