"""Document metadata schema. This is the *only* source of ground truth
(rubrics/ground_truth.py reads nothing else) and is generated before any
document prose exists -- see methodology.md §2.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    doc_id: str
    clause_type: Literal[1, 2, 3, 4]
    split: Literal["validation", "test"]

    # Clause type 1 (descriptive): one of "tax" | "invoices" | "contracts"
    doc_type: Optional[str] = None

    # Clause type 2 (conjunctive + threshold): all docs are invoices
    amount_usd: Optional[float] = None

    # Clause type 3 (relational)
    project_codename: Optional[str] = None
    mentioned_client: Optional[str] = None

    # Clause type 4 (negative/exclusionary): all docs are contracts
    is_superseded: Optional[bool] = None

    # Audit trail: which seeded draw produced this row's variable fields.
    seed_trace: dict = Field(default_factory=dict)
