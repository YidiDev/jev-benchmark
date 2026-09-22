"""Stage A of CT10 corpus generation: structured metadata only, zero API
cost. Produces 100 students, each with a latent ability parameter and a
per-question true score derived from it -- the sole ground truth this
benchmark grades models against.

Ability model: each student's ability ~ Beta(2,2) (symmetric, bounded to
(0,1), moderate spread) -- a single latent parameter that correlates a
student's performance across all 30 questions, per the user's explicit
choice over fully independent per-question randomness (real students are
consistent across a test, not random per question). Per-question true
score: `ability` plus independent Gaussian noise (so ability is not
perfectly deterministic -- a strong student can still slip on one
question, and vice versa), clipped to [0,1], scaled to that question's
point value and rounded to the nearest integer level.

Run: `python -m examgrade.generate_metadata`
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.constants import sub_rng
from examgrade.questions import EXAM_QUESTIONS
from examgrade.schema import StudentMetadata

MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.jsonl"

N_STUDENTS = 100
ABILITY_NOISE_SD = 0.15  # per-question performance noise around a student's ability


def sample_student_ability(rng) -> float:
    return rng.betavariate(2, 2)


def sample_true_score(ability: float, points: int, rng) -> int:
    noise = rng.gauss(0, ABILITY_NOISE_SD)
    ratio = min(max(ability + noise, 0.0), 1.0)
    return round(ratio * points)


def generate_all() -> list[StudentMetadata]:
    students = []
    for i in range(1, N_STUDENTS + 1):
        student_id = f"student_{i:03d}"
        rng = sub_rng(f"examgrade_student::{student_id}")
        ability = sample_student_ability(rng)
        scores = {q.id: sample_true_score(ability, q.points, rng) for q in EXAM_QUESTIONS}
        students.append(
            StudentMetadata(
                student_id=student_id,
                ability=ability,
                scores=scores,
                total_true_score=sum(scores.values()),
                seed_trace={"ability": ability},
            )
        )
    return students


def write_manifest(students: list[StudentMetadata]) -> None:
    with MANIFEST_PATH.open("w") as f:
        for s in students:
            f.write(s.model_dump_json() + "\n")
    print(f"Wrote {len(students)} student metadata rows to {MANIFEST_PATH}")


def load_manifest() -> list[StudentMetadata]:
    students = []
    with MANIFEST_PATH.open() as f:
        for line in f:
            if line.strip():
                students.append(StudentMetadata(**json.loads(line)))
    return students


if __name__ == "__main__":
    students = generate_all()
    write_manifest(students)

    totals = [s.total_true_score for s in students]
    abilities = [s.ability for s in students]
    print(f"Total score range: {min(totals)}-{max(totals)}, mean={sum(totals)/len(totals):.1f}")
    print(f"Ability range: {min(abilities):.3f}-{max(abilities):.3f}, mean={sum(abilities)/len(abilities):.3f}")

    import statistics

    correlation = statistics.correlation(abilities, totals) if len(abilities) > 1 else None
    print(f"Correlation(ability, total_true_score): {correlation:.4f}")
