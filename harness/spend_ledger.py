"""Append-only USD spend ledger, enforced against a hard budget.

Every paid API call (Sonnet 5 corpus generation, Haiku arm runs, Jev/OpenJev
if their free tiers are ever exceeded) must go through `record_spend` so the
running total in `results/spend_ledger.jsonl` stays authoritative. This is
what methodology.md §5 and results.md's cost tables are built from — actual
logged spend, not list-price estimates.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from harness.constants import ANTHROPIC_BUDGET_USD, ANTHROPIC_WARN_USD, PRICING

LEDGER_PATH = Path(__file__).resolve().parent.parent / "results" / "spend_ledger.jsonl"


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class SpendRecord:
    ts: float
    source: str  # e.g. "corpus_generation", "haiku_arm"
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    note: str = ""
    # Prompt-cache token counts (0 for arms/calls that don't use caching).
    # input_tokens above is the *uncached* portion only -- see cost_for.
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


def _provider(model: str) -> str:
    return "anthropic" if model.startswith("claude-") else "other"


def cost_for(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """input_tokens is the *uncached* input token count -- when a call uses
    prompt caching, pass the cache write/read counts separately so each
    portion is priced at its own rate (see PRICING's cache_write_per_mtok /
    cache_read_per_mtok, only populated for caching-capable models)."""
    rates = PRICING[model]
    cost = (
        input_tokens * rates["input_per_mtok"] / 1_000_000
        + output_tokens * rates["output_per_mtok"] / 1_000_000
    )
    if cache_creation_tokens:
        cost += cache_creation_tokens * rates["cache_write_per_mtok"] / 1_000_000
    if cache_read_tokens:
        cost += cache_read_tokens * rates["cache_read_per_mtok"] / 1_000_000
    return cost


def cumulative_spend(provider: str = "anthropic") -> float:
    if not LEDGER_PATH.exists():
        return 0.0
    total = 0.0
    for line in LEDGER_PATH.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if _provider(row["model"]) == provider:
            total += row["cost_usd"]
    return total


def record_spend(
    source: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    note: str = "",
    dry_run: bool = False,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Log a paid call and return its cost. Raises BudgetExceeded if this
    call would push cumulative Anthropic spend past ANTHROPIC_BUDGET_USD, or
    warns (via return-side note) once past ANTHROPIC_WARN_USD.

    dry_run=True computes and returns cost without writing to the ledger or
    enforcing the budget -- used for pre-flight cost estimates.

    cache_creation_tokens / cache_read_tokens: pass through from
    response.usage for arms using Anthropic prompt caching (see
    arms/haiku.py); input_tokens should then be the *uncached* portion only,
    so no token is double-counted across the three rates.
    """
    cost = cost_for(model, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
    if dry_run:
        return cost

    provider = _provider(model)
    if provider == "anthropic":
        projected = cumulative_spend("anthropic") + cost
        if projected > ANTHROPIC_BUDGET_USD:
            raise BudgetExceeded(
                f"Recording this ${cost:.4f} {model} call would bring cumulative "
                f"Anthropic spend to ${projected:.4f}, over the ${ANTHROPIC_BUDGET_USD:.2f} "
                "budget. Stopping -- ask the user for more credit before proceeding."
            )

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = SpendRecord(
        ts=time.time(),
        source=source,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        note=note,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
    )
    with LEDGER_PATH.open("a") as f:
        f.write(json.dumps(record.__dict__) + "\n")

    if provider == "anthropic":
        total = cumulative_spend("anthropic")
        if total > ANTHROPIC_WARN_USD:
            print(
                f"[spend_ledger] WARNING: cumulative Anthropic spend is ${total:.4f}, "
                f"past the ${ANTHROPIC_WARN_USD:.2f} warn threshold "
                f"(${ANTHROPIC_BUDGET_USD:.2f} hard budget). Consider pausing."
            )
    return cost


def summarize() -> dict:
    """Aggregate spend by (source, model) for reporting into results.md."""
    if not LEDGER_PATH.exists():
        return {}
    out: dict[str, dict] = {}
    for line in LEDGER_PATH.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = f"{row['source']}::{row['model']}"
        agg = out.setdefault(
            key,
            {"source": row["source"], "model": row["model"], "input_tokens": 0,
             "output_tokens": 0, "cost_usd": 0.0, "calls": 0,
             "cache_creation_tokens": 0, "cache_read_tokens": 0},
        )
        agg["input_tokens"] += row["input_tokens"]
        agg["output_tokens"] += row["output_tokens"]
        agg["cost_usd"] += row["cost_usd"]
        agg["calls"] += 1
        agg["cache_creation_tokens"] += row.get("cache_creation_tokens", 0)
        agg["cache_read_tokens"] += row.get("cache_read_tokens", 0)
    return out


if __name__ == "__main__":
    summary = summarize()
    if not summary:
        print("No spend recorded yet.")
    else:
        total = 0.0
        for key, agg in sorted(summary.items()):
            cache_note = ""
            if agg["cache_creation_tokens"] or agg["cache_read_tokens"]:
                cache_note = (
                    f" cache_write={agg['cache_creation_tokens']:<9} cache_read={agg['cache_read_tokens']:<9}"
                )
            print(
                f"{agg['source']:<24} {agg['model']:<20} calls={agg['calls']:<5} "
                f"in={agg['input_tokens']:<9} out={agg['output_tokens']:<9}"
                f"{cache_note} ${agg['cost_usd']:.4f}"
            )
            total += agg["cost_usd"]
        print(f"\nTotal logged spend: ${total:.4f}")
        anthropic_total = cumulative_spend("anthropic")
        print(
            f"Anthropic spend: ${anthropic_total:.4f} / ${ANTHROPIC_BUDGET_USD:.2f} budget "
            f"({ANTHROPIC_BUDGET_USD - anthropic_total:.4f} remaining)"
        )
