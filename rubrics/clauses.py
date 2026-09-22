"""Builds the actual rubric text handed to every arm: `criteria` (folder
display name -> description) and `instructions` (rule text with folder
placeholders resolved to that condition's display names).

Decomposition is fixed per methodology.md §3: one Choice question per
document, full rubric as criteria, identical structure across every arm and
condition. This module is the single place that wording is assembled, so a
wording change here applies uniformly everywhere (the §8 discipline).
"""

from __future__ import annotations

from dataclasses import dataclass

from rubrics.clause_specs import CLAUSE_SPECS
from rubrics.conditions import FolderMapping, folder_mapping
from rubrics.shuffle_control import shuffle_mapping


@dataclass
class Rubric:
    clause_type: int
    condition: str  # "A" | "B" | "C" | "SHUFFLE"
    instructions: str
    criteria: dict[str, str]  # display_name -> description
    folders: list[str]  # display names, in canonical order
    mapping: FolderMapping  # canonical_id -> display_name, for scoring


def build_rubric(clause_type: int, condition: str) -> Rubric:
    spec = CLAUSE_SPECS[clause_type]

    if condition == "SHUFFLE":
        mapping = shuffle_mapping(clause_type)
    elif condition in ("A", "B", "C"):
        mapping = folder_mapping(clause_type, condition)
    else:
        raise ValueError(f"unknown condition {condition!r}")

    instructions = spec.rule_text_fn().format(**mapping)
    criteria = {mapping[canonical]: spec.descriptions[canonical] for canonical in spec.folders}
    folders = [mapping[c] for c in spec.folders]

    return Rubric(
        clause_type=clause_type,
        condition=condition,
        instructions=instructions,
        criteria=criteria,
        folders=folders,
        mapping=mapping,
    )
