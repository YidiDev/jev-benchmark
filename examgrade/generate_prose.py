"""Stage B of CT10 corpus generation: student exam answers via Claude
Sonnet 5. One call generates all 30 of a single student's answers (batch
size 1 per student, matching CT9's lesson: batching multiple 30-item
forms per call reliably broke output-format-following at that Q&A
density; exam answers are even longer -- full paragraphs, not 1-2
sentences -- so batching students together would only be riskier).

Deliberately not Haiku, same rationale as corpus/generate_prose.py and
qtree/generate_prose.py -- Haiku is one of the arms under test.

Run: `python -m examgrade.generate_prose [--limit N]`
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import anthropic

import harness.env  # noqa: F401 -- loads .env before any client init
from examgrade.generate_metadata import load_manifest
from examgrade.prose_prompts import build_answer_brief
from examgrade.questions import EXAM_QUESTIONS
from harness.spend_ledger import BudgetExceeded, record_spend

MODEL = "claude-sonnet-5"
PRICING_KEY = "claude-sonnet-5"
DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"

ANSWER_START = "===ANSWER {qid}==="
ANSWER_END = "===END==="

SYSTEM_PROMPT = """You write realistic AP World History short-answer exam responses for a grading benchmark corpus. \
For each question you are given an instruction describing exactly what the answer should and should not correctly \
convey -- follow it precisely, since it encodes the exact partial credit this answer is meant to earn. Write in the \
voice of an actual student under time pressure: natural paragraph prose, not bullet points or headers. Do not use \
meta-language about points, rubrics, or grading anywhere in the answer text itself. Vary phrasing and quality across \
different answers so they don't read as templated."""


def _build_batch_prompt(student_id: str, briefs: list[dict]) -> str:
    parts = [
        f"Write all 30 exam answers for student {student_id}. For each question, output it wrapped "
        f"exactly like this (including the markers on their own lines):\n\n"
        f"{ANSWER_START.format(qid='<question_id>')}\n<answer text>\n{ANSWER_END}\n\n"
        "Do not add any commentary outside the markers. Here are the questions and instructions:\n"
    ]
    for b in briefs:
        parts.append(
            f"\n---\nquestion_id: {b['question_id']}\n"
            f"exam question: {b['prompt']}\n"
            f"target score: {b['true_score']}/{b['max_points']}\n"
            f"writing style: {b['style_guide']}\n"
            f"instruction: {b['instruction']}\n"
        )
    return "".join(parts)


def _parse_response(text: str, expected_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    pattern = re.compile(r"===ANSWER\s+(\S+)===\s*(.*?)\s*===END===", re.DOTALL)
    for match in pattern.finditer(text):
        qid, body = match.group(1).strip(), match.group(2).strip()
        out[qid] = body

    missing = [q for q in expected_ids if q not in out]
    if missing:
        # Lenient fallback (same fix as qtree/generate_prose.py): take
        # everything from a start marker through the next start marker or
        # end-of-text, in case the model omitted a closing marker.
        loose_pattern = re.compile(r"===ANSWER\s+(\S+)===\s*(.*?)(?====ANSWER\s+\S+===|\Z)", re.DOTALL)
        for match in loose_pattern.finditer(text):
            qid, body = match.group(1).strip(), match.group(2).strip()
            body = re.sub(r"===END===\s*$", "", body).strip()
            if qid not in out and body:
                out[qid] = body
        missing = [q for q in expected_ids if q not in out]
    if missing:
        raise ValueError(f"response missing answers: {missing}")
    return out


def generate_prose(limit: int | None = None, dry_run: bool = False) -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    students = load_manifest()
    if limit is not None:
        students = students[:limit]

    todo = [s for s in students if not (DOCUMENTS_DIR / f"{s.student_id}.txt").exists()]
    print(f"{len(students)} total students, {len(todo)} not yet generated.")
    if not todo:
        return

    client = None if dry_run else anthropic.Anthropic()

    for student in todo:
        briefs = [build_answer_brief(q, student.scores[q.id], student.student_id) for q in EXAM_QUESTIONS]
        prompt = _build_batch_prompt(student.student_id, briefs)
        expected_ids = [q.id for q in EXAM_QUESTIONS]

        if dry_run:
            print(f"[dry-run] {student.student_id}: {len(briefs)} answers queued")
            continue

        response = client.messages.create(
            model=MODEL,
            max_tokens=16_000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage

        try:
            cost = record_spend(
                source="examgrade_corpus_generation",
                model=PRICING_KEY,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                note=f"student {student.student_id}, 30 answers",
            )
        except BudgetExceeded as e:
            print(f"BUDGET EXCEEDED, stopping: {e}")
            raise

        answers = _parse_response(text, expected_ids)

        lines = []
        for q in EXAM_QUESTIONS:
            lines.append(f"Q ({q.id}, {q.points} pts): {q.prompt}")
            lines.append(f"A: {answers[q.id]}")
            lines.append("")
        (DOCUMENTS_DIR / f"{student.student_id}.txt").write_text("\n".join(lines))

        print(
            f"{student.student_id}: 30 answers written, "
            f"in={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generate_prose(limit=args.limit, dry_run=args.dry_run)
