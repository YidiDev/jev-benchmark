"""Stage B of CT9 corpus generation: natural-language Q&A transcripts via
Claude Sonnet 5 (same non-Haiku rationale as corpus/generate_prose.py --
avoids a self-consistency advantage for the Haiku arm under test).

Each output file (qtree/documents/{form_id}.txt) is a 30-question intake
transcript: every question's text followed by a natural-language answer
that faithfully encodes that form's structured answer (see
qtree/prose_prompts.py). This transcript is the "state" every arm receives
-- ground truth is never derived from it, only from the structured
qtree/manifest.jsonl answers.

Run: `python -m qtree.generate_prose [--batch-size 3] [--limit N]`
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import anthropic

import harness.env  # noqa: F401  (loads .env before any client is constructed)
from harness.spend_ledger import BudgetExceeded, record_spend
from qtree.generate_metadata import load_manifest
from qtree.prose_prompts import build_form_spec
from qtree.questions import SPECIAL_QUESTIONS, STANDARD_QUESTIONS

MODEL = "claude-sonnet-5"
PRICING_KEY = "claude-sonnet-5"
DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"

FORM_START = "===FORM {form_id}==="
FORM_END = "===END==="

ALL_QUESTIONS = STANDARD_QUESTIONS + [
    type("Q", (), {"id": q.id, "text": q.text})() for q in SPECIAL_QUESTIONS
]  # unified iterable with .id/.text for building the transcript skeleton

SYSTEM_PROMPT = """You write realistic natural-language answers for a compliance/eligibility intake questionnaire \
benchmark corpus. For each question in a form, you are given the TRUE underlying answer/fact it must convey and \
must write a natural, free-text response a real person might actually type or say -- varied register (casual, \
formal, terse, rambling, per the style given) but the true answer must always remain clearly, unambiguously \
recoverable from the phrasing; never introduce genuine doubt about which underlying answer is meant. \
Do not use meta-language about forms, folders, categories, or scoring anywhere in the text. \
Follow each question's specific length instruction exactly (e.g. '3 sentences or less' means literally count \
sentences and stay at or under 3; '4 or more sentences' means literally write 4+ sentences). \
Vary phrasing across different forms in the same batch so they don't read as templated copies of each other."""


def _build_batch_prompt(specs: list[dict]) -> str:
    parts = [
        "Write the following intake questionnaire transcripts. For each one, output it wrapped exactly like "
        f"this (including the markers on their own lines):\n\n{FORM_START.format(form_id='<form_id>')}\n"
        "Q1: <question text>\nA1: <answer>\n...\nQ30: <question text>\nA30: <answer>\n"
        f"{FORM_END}\n\n"
        "Answer every question in order Q1-Q30, matching the question order given below exactly. "
        "Do not add any commentary outside the markers. Here are the forms to write:\n"
    ]
    for spec in specs:
        brief_lines = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(spec["briefs"]))
        parts.append(
            f"\n---\nform_id: {spec['form_id']}\n"
            f"overall style: {spec['style_guide']}\n"
            f"questions and required answer content, in order:\n{brief_lines}\n"
        )
    return "".join(parts)


def _parse_batch_response(text: str, expected_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    # Primary pattern: properly closed with ===END===.
    closed = re.compile(r"===FORM\s+(\S+)===\s*(.*?)\s*===END===", re.DOTALL)
    for match in closed.finditer(text):
        form_id, body = match.group(1).strip(), match.group(2).strip()
        out[form_id] = body

    # Fallback: the model occasionally omits the closing ===END=== marker
    # even well under its token budget (observed empirically, not a
    # truncation issue -- output_tokens stayed far below max_tokens on
    # every occurrence). Accept content from a ===FORM id=== marker through
    # either the next ===FORM=== marker or end of text.
    if len(out) < len(expected_ids):
        open_pattern = re.compile(r"===FORM\s+(\S+)===")
        starts = list(open_pattern.finditer(text))
        for i, m in enumerate(starts):
            form_id = m.group(1).strip()
            if form_id in out:
                continue
            body_start = m.end()
            body_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
            body = text[body_start:body_end]
            body = re.sub(r"===END===\s*$", "", body).strip()
            if body:
                out[form_id] = body

    missing = [d for d in expected_ids if d not in out]
    if missing:
        raise ValueError(f"batch response missing forms: {missing}")
    return out


def _max_tokens_for_batch(n_forms: int) -> int:
    # ~30 answers/form, avg ~25 words/answer incl. the 3 longer special
    # ones, plus question-text echo -> generous per-form budget. A single
    # real form used ~3957 output tokens -- batching multiple 30-question
    # forms per call was found empirically unreliable (the model would
    # write one form fully and never properly close it or start the next),
    # not a token-budget problem specifically -- so batch_size=1 is the
    # default (see generate_prose()'s default), and this stays generous.
    return min(max(n_forms * 6000, 6000), 32_000)


def generate_prose(batch_size: int = 1, limit: int | None = None, dry_run: bool = False) -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    if limit is not None:
        manifest = manifest[:limit]

    todo = [m for m in manifest if not (DOCUMENTS_DIR / f"{m.form_id}.txt").exists()]
    print(f"{len(manifest)} total forms, {len(todo)} not yet generated.")
    if not todo:
        return

    client = None if dry_run else anthropic.Anthropic()

    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        specs = [build_form_spec(m) for m in batch]
        prompt = _build_batch_prompt(specs)
        expected_ids = [s["form_id"] for s in specs]

        if dry_run:
            print(f"[dry-run] batch {i // batch_size}: {expected_ids}")
            continue

        response = client.messages.create(
            model=MODEL,
            max_tokens=_max_tokens_for_batch(len(batch)),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage

        try:
            cost = record_spend(
                source="qtree_corpus_generation",
                model=PRICING_KEY,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                note=f"batch {i // batch_size}, {len(batch)} forms: {expected_ids}",
            )
        except BudgetExceeded as e:
            print(f"BUDGET EXCEEDED, stopping: {e}")
            raise

        docs = _parse_batch_response(text, expected_ids)
        for form_id, body in docs.items():
            (DOCUMENTS_DIR / f"{form_id}.txt").write_text(body + "\n")

        print(
            f"batch {i // batch_size}: {len(docs)} forms written, "
            f"in={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generate_prose(batch_size=args.batch_size, limit=args.limit, dry_run=args.dry_run)
