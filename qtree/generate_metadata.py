"""Stage A of CT9 corpus generation: structured metadata only, zero API
cost. Stratifies to exactly 10 test + 2 validation forms per terminal
folder (5 folders x 12 = 60 forms total), matching the CT1-8 pattern.

Each candidate form_id's answers come from qtree.questions.sample_form_answers,
seeded uniquely per form_id -- draws are tried in a deterministic sequence
(candidate index 0, 1, 2, ...) until every folder's quota is filled, so the
whole process is reproducible from MASTER_SEED alone.

Run: `python -m qtree.generate_metadata`
"""

from __future__ import annotations

import json
from pathlib import Path

from qtree.questions import sample_form_answers
from qtree.schema import FormMetadata
from qtree.tree import FOLDERS, true_folder

MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.jsonl"

PER_FOLDER_TEST = 10
PER_FOLDER_VALIDATION = 2


def generate_all() -> list[FormMetadata]:
    quotas = {"test": PER_FOLDER_TEST, "validation": PER_FOLDER_VALIDATION}
    forms: list[FormMetadata] = []

    for split, per_folder in quotas.items():
        counts = {f: 0 for f in FOLDERS}
        kept: list[tuple[str, dict, str]] = []
        candidate_idx = 0
        target_total = per_folder * len(FOLDERS)
        # Use a split-specific candidate namespace so test/validation draws
        # never collide on the same form_id.
        while len(kept) < target_total:
            candidate_idx += 1
            form_id = f"qt_{split}_cand_{candidate_idx:05d}"
            answers = sample_form_answers(form_id)
            folder = true_folder(answers)
            if counts[folder] >= per_folder:
                continue
            counts[folder] += 1
            kept.append((form_id, answers, folder))

        for i, (_cand_id, answers, folder) in enumerate(kept, start=1):
            final_id = f"qt_{split[:2]}_{i:03d}"
            forms.append(
                FormMetadata(
                    form_id=final_id,
                    split=split,
                    answers=answers,
                    true_folder=folder,
                    seed_trace={"true_folder": folder},
                )
            )

    return forms


def write_manifest(forms: list[FormMetadata]) -> None:
    with MANIFEST_PATH.open("w") as f:
        for form in forms:
            f.write(form.model_dump_json() + "\n")
    print(f"Wrote {len(forms)} form metadata rows to {MANIFEST_PATH}")


def load_manifest() -> list[FormMetadata]:
    forms = []
    with MANIFEST_PATH.open() as f:
        for line in f:
            forms.append(FormMetadata(**json.loads(line)))
    return forms


if __name__ == "__main__":
    forms = generate_all()
    write_manifest(forms)
    from collections import Counter

    for split in ("test", "validation"):
        dist = Counter(f.true_folder for f in forms if f.split == split)
        print(f"  {split}: {dict(sorted(dist.items()))}")
