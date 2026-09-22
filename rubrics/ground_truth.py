"""Deterministic ground truth. Pure functions of structured metadata only --
never document prose, never rubric text -- per the independence control in
test-plan.md §5.3 and methodology.md §2.
"""

from __future__ import annotations

from corpus.schema import DocumentMetadata
from rubrics.clause_specs import CT2_THRESHOLD_USD, CT3_FIXTURES
from rubrics.conditions import FolderMapping, folder_mapping
from rubrics.shuffle_control import shuffle_mapping


def canonical_folder(metadata: DocumentMetadata) -> str:
    """The correct canonical folder id, independent of any condition's
    display names."""
    ct = metadata.clause_type

    if ct == 1:
        assert metadata.doc_type in {"tax", "invoices", "contracts"}
        return metadata.doc_type

    if ct == 2:
        assert metadata.amount_usd is not None
        return "large_invoices" if metadata.amount_usd > CT2_THRESHOLD_USD else "small_invoices"

    if ct == 3:
        client = metadata.mentioned_client
        if client is not None and client in CT3_FIXTURES.retainer_clients:
            return "retainer_clients"
        assert metadata.project_codename in CT3_FIXTURES.project_folder_map
        return CT3_FIXTURES.project_folder_map[metadata.project_codename]

    if ct == 4:
        assert metadata.is_superseded is not None
        return "archive" if metadata.is_superseded else "contracts"

    raise ValueError(f"unknown clause_type {ct}")


def correct_folder(
    metadata: DocumentMetadata,
    condition: str | None = None,
    shuffle: bool = False,
) -> str:
    """The correct *display* folder id for a given condition (A/B/C), or
    under the shuffle control if shuffle=True (condition is ignored in that
    case -- the shuffle control is always built on Condition B's opaque ids,
    per test-plan.md §5.1)."""
    canonical = canonical_folder(metadata)
    mapping: FolderMapping = (
        shuffle_mapping(metadata.clause_type) if shuffle else folder_mapping(metadata.clause_type, condition)
    )
    return mapping[canonical]
