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

CLAUSE_TYPES = (1, 2, 3, 4, 5, 6, 7, 8)

CLAUSE_TYPE_NAMES = {
    1: "descriptive",
    2: "conjunctive_threshold",
    3: "relational",
    4: "negative_exclusionary",
    # "Hard mode" clause types (added 2026-09-22, see methodology.md §12):
    # each targets one specific documented jev-1.13 weakness, in isolation,
    # so a drop in accuracy on a given type is attributable to one cause.
    5: "computed_threshold",  # arithmetic: sum stated line items, no stated total
    6: "temporal_reasoning",  # date comparison, no narrative "superseded" cue
    7: "multi_hop_relational",  # two chained lookups: team -> division -> program
    8: "long_context_distractor",  # CT1-style descriptive logic, buried in padding
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
#
# cache_write_per_mtok / cache_read_per_mtok are only meaningful for arms
# that use Anthropic prompt caching (see arms/haiku.py). Using 1-hour cache
# entries (2x base input price to write, vs 1.25x for 5-minute entries),
# because a (clause_type, condition) group is up to 180 sequential calls --
# a run slowdown could plausibly cross a 5-minute TTL mid-group and silently
# fall back to paying full price, whereas 1h has ample margin; break-even is
# 2 cache reads either way. Cache reads (hits) are 0.1x base input price
# regardless of TTL. Rates per
# platform.claude.com/docs/en/about-claude/pricing#prompt-caching
# (confirmed 2026-09-21). Arms that never populate cache token counts simply
# never hit those rates in harness/spend_ledger.py's cost_for().
PRICING = {
    "jev-1.13.0": {"input_per_mtok": 0.042, "output_per_mtok": 0.0},
    "jev-latest": {"input_per_mtok": 0.042, "output_per_mtok": 0.0},
    "openjev": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},  # Codiv free tier
    "claude-haiku-4-5": {
        "input_per_mtok": 1.00,
        "output_per_mtok": 5.00,
        "cache_write_per_mtok": 2.00,  # 1h cache write
        "cache_read_per_mtok": 0.10,
    },
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
}

# Hard budget guardrails. See results.md / conversation log: user-provided
# Anthropic credit was originally $5.00 total, shared across corpus
# generation (Sonnet 5) and the Haiku reference arm. Raised to $12.00 on
# 2026-09-22 to fund "hard mode" clause types CT5-CT8 (see methodology.md
# §12) at full scope, including a full Haiku comparison -- explicit user
# approval, after a cost projection (~$6.49 against $1.06 remaining at the
# time). Raised again to $12.50 the same day to finish the last 33 CT8
# predictions (run stopped 1 cent short of $12.00 with 99% of the run done).
# Raised again to $30.00 to fund CT9 "chained decision execution" (see
# methodology.md §13) -- multi-call chunked tree traversal with real
# compounding, explicit user approval ("total budget $30. go for it") after
# a rough ~$8-9.5 cost projection for the CT9 corpus + full Haiku run.
# Ledger-enforced in harness/spend_ledger.py.
ANTHROPIC_BUDGET_USD = 30.00
ANTHROPIC_WARN_USD = 28.00  # stop and ask before crossing this
