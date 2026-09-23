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

# --- Estimated self-hosted compute cost (USD), NOT real metered spend. ---
#
# PRICING above (and results/spend_ledger.jsonl, and ANTHROPIC_BUDGET_USD) is
# the *actual* money spent running this benchmark -- nli-bart and emb-bge ran
# locally on this machine's own hardware, and openjev ran on Codiv's free
# hosted tier, so their real cost really was $0.00. But "$0.00" is a
# misleading number to put next to Jev/Haiku/Sonnet's real API pricing in a
# cost comparison: if you actually deployed nli-bart, emb-bge, or a
# self-hosted OpenJev, you would pay for the compute, just not through this
# benchmark's ledger. This table estimates that cost from a specific, stated
# hardware/throughput assumption per model, documented in methodology.md §17,
# so the estimate is auditable rather than a bare number. It is NEVER passed
# to record_spend() or counted against ANTHROPIC_BUDGET_USD -- it exists only
# for reporting (scripts/estimate_self_hosted_cost.py), computed once, after
# the fact, from real token counts (re-tokenized from the committed corpus
# for nli-bart/emb-bge, since those arms never logged token counts during the
# actual local run; reused directly from openjev's already-logged real input
# token counts, which recorded real usage even though PRICING["openjev"] is
# $0/$0).
#
# Assumptions (all budget/community cloud-GPU spot rates, 2026 ballpark,
# deliberately on the cheap end since "self-hosted" implies cost-consciously
# run, not a premium reserved instance):
#   - nli-bart (facebook/bart-large-mnli, ~407M params): a 16GB "T4-class"
#     GPU is far more than this model needs, but is the smallest commonly
#     rented cloud GPU tier -- $0.20/hr, ~2,000 input tok/s (encoder-only
#     forward pass, batch=1, one (premise, hypothesis) pair per candidate
#     folder -- see the HF zero-shot-classification pipeline's actual call
#     shape in arms/nli_bart.py). No output tokens (classification scores
#     only, nothing generated).
#   - emb-bge (BAAI/bge-m3, ~568M params): same T4-class tier, $0.20/hr,
#     ~1,800 input tok/s (slightly larger model, embedding forward pass).
#     No output tokens.
#   - openjev self-hosted (razorback16/openjev, DiffusionGemma 26B-A4B):
#     arms/openjev.py's own module docstring already documents this model's
#     real hardware requirement as "24GB-class GPU" (established when this
#     machine's RTX 3050 8GB was found insufficient) -- used here directly
#     rather than re-guessing. $0.40/hr for a 24GB-class budget cloud GPU
#     (RTX 4090/A10G-tier), ~4,000 input tok/s (prefill/encode-style
#     throughput scales well with parallelism regardless of the ~4B active
#     parameters per token). Output tokens are never logged for this arm
#     (Codiv's endpoint doesn't report them -- every openjev prediction
#     record shows output_tokens=0), so this estimate prices the input/
#     prompt side only; real self-hosted cost including generation would be
#     somewhat higher. output_per_mtok is set anyway, for schema uniformity
#     and in case a future logging fix populates real output token counts.
SELF_HOSTED_GPU_HOURLY_USD = {
    "t4_class_16gb": 0.20,
    "gpu_24gb_class": 0.40,
}
SELF_HOSTED_PRICING = {
    "nli-bart": {"input_per_mtok": 0.20 / (2_000 * 3_600) * 1_000_000, "output_per_mtok": 0.0},
    "emb-bge": {"input_per_mtok": 0.20 / (1_800 * 3_600) * 1_000_000, "output_per_mtok": 0.0},
    "openjev-self-hosted": {
        "input_per_mtok": 0.40 / (4_000 * 3_600) * 1_000_000,
        "output_per_mtok": 0.40 / (300 * 3_600) * 1_000_000,  # never exercised, see above
    },
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
# Raised again to $50.00 to fund CT10 "AP World History exam grading" (see
# methodology.md §14) -- explicit user approval ("approved budget for CT10
# is $50") after a ~$20-30 cost projection with overshoot margin. OpenJev
# (arms/openjev.py, qtree's OpenJev chunk arm, examgrade's OpenJev arm) is
# a free Codiv-hosted tier and does not draw against this budget at all.
# Raised again to $110.00 (see methodology.md §15) to fund a Sonnet 5 arm
# across CT1-8/CT9/CT10 -- full scope, matching Haiku's exact repeat/grid
# structure, revisiting the earlier decline of a Sonnet comparison
# (§11/§12) now that CT9/CT10 show Haiku underperforming Jev by a wider,
# more structurally interesting margin than CT1-8 ever did. Explicit user
# approval ("go for it all" + confirmed scope/budget via question prompt:
# full scope, $110 ceiling, matching Haiku's grid) after a ~$59.34
# cost projection derived directly from Haiku's own logged token totals
# (claude-sonnet-5 is priced at exactly 2x claude-haiku-4-5's per-token
# rate, so 2x Haiku's actual per-task-family spend is a tight estimate).
# Ledger-enforced in harness/spend_ledger.py.
ANTHROPIC_BUDGET_USD = 110.00
ANTHROPIC_WARN_USD = 105.00  # stop and ask before crossing this
