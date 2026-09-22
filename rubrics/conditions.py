"""Folder-name conditions A (semantic) / B (opaque) / C (misleading) from
test-plan.md §2, applied uniformly on top of each clause type's canonical
folders (rubrics/clause_specs.py).

A `FolderMapping` is always canonical_id -> display_name. Ground truth
(rubrics/ground_truth.py) is computed entirely in canonical-id space and
only translated to a display name at the very end, so the same logic works
unchanged across all three conditions.
"""

from __future__ import annotations

from functools import lru_cache

from harness.constants import sub_rng
from rubrics.clause_specs import CLAUSE_SPECS
from rubrics.rng_util import derangement, distinct_opaque_ids

FolderMapping = dict[str, str]  # canonical_id -> display_name


@lru_cache(maxsize=None)
def semantic_mapping(clause_type: int) -> FolderMapping:
    """Condition A: display name == canonical id (already self-descriptive)."""
    folders = CLAUSE_SPECS[clause_type].folders
    return {c: c for c in folders}


@lru_cache(maxsize=None)
def opaque_mapping(clause_type: int) -> FolderMapping:
    """Condition B: random opaque ids, no semantic content for NLI to score."""
    folders = CLAUSE_SPECS[clause_type].folders
    rng = sub_rng(f"folder_ids::ct{clause_type}")
    ids = distinct_opaque_ids(rng, len(folders))
    return dict(zip(folders, ids))


@lru_cache(maxsize=None)
def misleading_mapping(clause_type: int) -> FolderMapping:
    """Condition C: derangement of the semantic names -- every folder is
    labeled with a *different* folder's semantic name, so content-prior
    matching on the label text is systematically wrong."""
    folders = CLAUSE_SPECS[clause_type].folders
    if len(folders) < 2:
        # Can't derange a single-folder clause type; none of ours are this
        # small, but guard anyway.
        return semantic_mapping(clause_type)
    rng = sub_rng(f"misleading::ct{clause_type}")
    return derangement(folders, rng)


_BUILDERS = {"A": semantic_mapping, "B": opaque_mapping, "C": misleading_mapping}


def folder_mapping(clause_type: int, condition: str) -> FolderMapping:
    if condition not in _BUILDERS:
        raise ValueError(f"unknown condition {condition!r}")
    return _BUILDERS[condition](clause_type)
