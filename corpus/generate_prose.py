"""Stage B of corpus generation: document prose via Claude Sonnet 5.

Deliberately *not* Haiku -- Haiku is one of the arms under test, and using
it to author the documents it later classifies would risk a self-consistency
advantage (its own phrasing being more legible to itself). See
methodology.md §2. Every call is logged to harness/spend_ledger.py against
the shared $5.00 Anthropic budget.

Run: `python -m corpus.generate_prose [--batch-size 8] [--limit N]`
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import anthropic

import harness.env  # noqa: F401  (loads .env before any client is constructed)
from corpus.generate_metadata import load_manifest
from corpus.prose_prompts import build_doc_spec
from harness.spend_ledger import BudgetExceeded, record_spend

MODEL = "claude-sonnet-5"  # confirmed via GET /v1/models on 2026-09-21
PRICING_KEY = "claude-sonnet-5"
DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"

DOC_START = "===DOC {doc_id}==="
DOC_END = "===END==="

SYSTEM_PROMPT = """You write realistic-sounding business documents for a document-sorting benchmark corpus. \
Each document must faithfully include the specific facts given for it -- these facts are load-bearing, not optional color. \
Do not use meta-language about folders, categories, or sorting rules anywhere in the text; the document should read as \
an ordinary real-world business document, not as an example written for a classifier. \
Follow the target length given for each individual document -- lengths vary by document, some much longer than others. \
Vary names, dates, and phrasing across documents in the same batch so they don't read as templated copies of each other."""


def _build_batch_prompt(specs: list[dict]) -> str:
    parts = [
        "Write the following documents. For each one, output it wrapped exactly like this "
        f"(including the markers on their own lines):\n\n{DOC_START.format(doc_id='<doc_id>')}\n"
        "<document text>\n"
        f"{DOC_END}\n\n"
        "Do not add any commentary outside the markers. Here are the documents to write:\n"
    ]
    for spec in specs:
        parts.append(
            f"\n---\ndoc_id: {spec['doc_id']}\n"
            f"format: {spec['style_guide']}\n"
            f"target length: {spec['length_hint']}\n"
            f"required facts: {spec['facts']}\n"
        )
    return "".join(parts)


def _max_tokens_for_batch(specs: list[dict]) -> int:
    """Dynamic per-batch output budget -- CT8's padded documents (~500-700
    words each) need far more headroom than CT1-7's ~120-220-word ones; a
    fixed 4096-token ceiling silently truncates a batch of 8 CT8 docs."""
    total_estimate = sum(spec.get("max_tokens_estimate", 400) for spec in specs)
    return min(max(total_estimate, 4096), 32_000)


def _parse_batch_response(text: str, expected_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    pattern = re.compile(r"===DOC\s+(\S+)===\s*(.*?)\s*===END===", re.DOTALL)
    for match in pattern.finditer(text):
        doc_id, body = match.group(1).strip(), match.group(2).strip()
        out[doc_id] = body
    missing = [d for d in expected_ids if d not in out]
    if missing:
        raise ValueError(f"batch response missing documents: {missing}")
    return out


def generate_prose(batch_size: int = 8, limit: int | None = None, dry_run: bool = False) -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    if limit is not None:
        manifest = manifest[:limit]

    todo = [m for m in manifest if not (DOCUMENTS_DIR / f"{m.doc_id}.txt").exists()]
    print(f"{len(manifest)} total docs, {len(todo)} not yet generated.")
    if not todo:
        return

    client = None if dry_run else anthropic.Anthropic()

    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        specs = [build_doc_spec(m) for m in batch]
        prompt = _build_batch_prompt(specs)
        expected_ids = [s["doc_id"] for s in specs]

        if dry_run:
            print(f"[dry-run] batch {i // batch_size}: {expected_ids}")
            continue

        response = client.messages.create(
            model=MODEL,
            max_tokens=_max_tokens_for_batch(specs),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage

        try:
            cost = record_spend(
                source="corpus_generation",
                model=PRICING_KEY,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                note=f"batch {i // batch_size}, {len(batch)} docs: {expected_ids}",
            )
        except BudgetExceeded as e:
            print(f"BUDGET EXCEEDED, stopping: {e}")
            raise

        docs = _parse_batch_response(text, expected_ids)
        for doc_id, body in docs.items():
            (DOCUMENTS_DIR / f"{doc_id}.txt").write_text(body + "\n")

        print(
            f"batch {i // batch_size}: {len(docs)} docs written, "
            f"in={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generate_prose(batch_size=args.batch_size, limit=args.limit, dry_run=args.dry_run)
