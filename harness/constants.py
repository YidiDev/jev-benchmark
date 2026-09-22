"""Shared constants: master seed, clause-type registry, pricing table, budgets.

MASTER_SEED and the per-purpose sub-seeding scheme are documented in
methodology.md §1. Never use the global `random` module state directly —
always derive a `random.Random` instance via `sub_rng`.
"""

from __future__ import annotations

import random
import zlib

# Drafted 2026-09-21, per test-plan.md's own dateline.
MASTER_SEED = 20260921

CLAUSE_TYPES = (1, 2, 3, 4)

CLAUSE_TYPE_NAMES = {
    1: "descriptive",
    2: "conjunctive_threshold",
    3: "relational",
    4: "negative_exclusionary",
}

CONDITIONS = ("A", "B", "C")  # semantic, opaque, misleading

CONDITION_NAMES = {
    "A": "semantic",
    "B": "opaque",
    "C": "misleading",
}

TEST_DOCS_PER_CLAUSE = 50
VALIDATION_DOCS_PER_CLAUSE = 10

REPEATS = 3


def sub_rng(purpose: str) -> random.Random:
    """Deterministic, independently-auditable RNG stream for one purpose.

    Each purpose gets its own `random.Random` instance seeded from
    MASTER_SEED XORed with a stable hash of the purpose string, so streams
    never collide and any single stream can be reproduced from
    (MASTER_SEED, purpose) alone without replaying the others.
    """
    purpose_hash = zlib.crc32(purpose.encode("utf-8"))
    return random.Random(MASTER_SEED ^ purpose_hash)


# --- Pricing (USD), as verified against provider docs on 2026-09-21. ---
# See methodology.md §5 for sources. Re-verify before any pricing change.
PRICING = {
    "jev-1.13.0": {"input_per_mtok": 0.042, "output_per_mtok": 0.0},
    "jev-latest": {"input_per_mtok": 0.042, "output_per_mtok": 0.0},
    "openjev": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},  # Codiv free tier
    "claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
}

# Hard budget guardrails. See results.md / conversation log: user-provided
# Anthropic credit is $5.00 total, shared across corpus generation (Sonnet 5)
# and the Haiku reference arm. Ledger-enforced in harness/spend_ledger.py.
ANTHROPIC_BUDGET_USD = 5.00
ANTHROPIC_WARN_USD = 4.00  # stop and ask before crossing this
