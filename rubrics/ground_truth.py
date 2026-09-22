"""Deterministic ground truth. Pure functions of structured metadata only --
never document prose, never rubric text -- per the independence control in
test-plan.md §5.3 and methodology.md §2.
"""

from __future__ import annotations

from datetime import date

from corpus.schema import DocumentMetadata
from rubrics.clause_specs import CT2_THRESHOLD_USD, CT3_FIXTURES, CT5_THRESHOLD_USD, CT7_FIXTURES
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

    if ct == 5:
        assert metadata.line_items is not None and len(metadata.line_items) > 0
        total = sum(metadata.line_items)
        return "over_budget" if total > CT5_THRESHOLD_USD else "under_budget"

    if ct == 6:
        assert metadata.effective_date is not None and metadata.reference_date is not None
        effective = date.fromisoformat(metadata.effective_date)
        reference = date.fromisoformat(metadata.reference_date)
        assert effective != reference  # corpus generation must never produce a tie
        return "current_version" if effective > reference else "prior_version"

    if ct == 7:
        assert metadata.team in CT7_FIXTURES.team_to_division
        division = CT7_FIXTURES.team_to_division[metadata.team]
        return CT7_FIXTURES.division_to_program[division]

    if ct == 8:
        assert metadata.doc_type in {"tax_form", "invoice_doc", "contract_doc"}
        return metadata.doc_type

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
