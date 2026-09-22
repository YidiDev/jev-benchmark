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


def _provider(model: str) -> str:
    return "anthropic" if model.startswith("claude-") else "other"


def cost_for(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING[model]
    return (
        input_tokens * rates["input_per_mtok"] / 1_000_000
        + output_tokens * rates["output_per_mtok"] / 1_000_000
    )


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
) -> float:
    """Log a paid call and return its cost. Raises BudgetExceeded if this
    call would push cumulative Anthropic spend past ANTHROPIC_BUDGET_USD, or
    warns (via return-side note) once past ANTHROPIC_WARN_USD.

    dry_run=True computes and returns cost without writing to the ledger or
    enforcing the budget -- used for pre-flight cost estimates.
    """
    cost = cost_for(model, input_tokens, output_tokens)
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
             "output_tokens": 0, "cost_usd": 0.0, "calls": 0},
        )
        agg["input_tokens"] += row["input_tokens"]
        agg["output_tokens"] += row["output_tokens"]
        agg["cost_usd"] += row["cost_usd"]
        agg["calls"] += 1
    return out


if __name__ == "__main__":
    summary = summarize()
    if not summary:
        print("No spend recorded yet.")
    else:
        total = 0.0
        for key, agg in sorted(summary.items()):
            print(
                f"{agg['source']:<24} {agg['model']:<20} calls={agg['calls']:<5} "
                f"in={agg['input_tokens']:<9} out={agg['output_tokens']:<9} "
                f"${agg['cost_usd']:.4f}"
            )
            total += agg["cost_usd"]
        print(f"\nTotal logged spend: ${total:.4f}")
        anthropic_total = cumulative_spend("anthropic")
        print(
            f"Anthropic spend: ${anthropic_total:.4f} / ${ANTHROPIC_BUDGET_USD:.2f} budget "
            f"({ANTHROPIC_BUDGET_USD - anthropic_total:.4f} remaining)"
        )
