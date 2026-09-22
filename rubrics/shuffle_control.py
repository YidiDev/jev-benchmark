"""The shuffle control, test-plan.md §5.1.

Same corpus, same opaque folder IDs as Condition B, but the rubric clause
each canonical folder maps to is permuted. If an arm is genuinely
conditioning on the rubric, its accuracy should track the *permuted*
assignment -- following the rubric to the semantically "wrong" folder. If it
still lands on the semantically sensible folder, it's using content priors
and the headline result is an artifact.

Implemented as composition: pick a derangement pi of canonical ids, then
shuffled_display(c) = opaque_mapping(pi(c)). Same opaque id set as Condition
B (required by the control), different clause-to-id pairing.
"""

from __future__ import annotations

from functools import lru_cache

from harness.constants import sub_rng
from rubrics.clause_specs import CLAUSE_SPECS
from rubrics.conditions import FolderMapping, opaque_mapping
from rubrics.rng_util import derangement


@lru_cache(maxsize=None)
def clause_permutation(clause_type: int) -> dict[str, str]:
    """canonical_id -> canonical_id, a derangement distinct from the one used
    for Condition C (different seed purpose -> independent draw)."""
    folders = CLAUSE_SPECS[clause_type].folders
    rng = sub_rng(f"shuffle_control::ct{clause_type}")
    return derangement(folders, rng)


@lru_cache(maxsize=None)
def shuffle_mapping(clause_type: int) -> FolderMapping:
    """canonical_id -> opaque display name, permuted per clause_permutation."""
    pi = clause_permutation(clause_type)
    opaque = opaque_mapping(clause_type)
    return {canonical: opaque[pi[canonical]] for canonical in pi}
