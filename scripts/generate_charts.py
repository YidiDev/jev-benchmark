"""Generates every chart used in README.md from the committed results
data (results/predictions/*.jsonl, results/spend_ledger.jsonl). Pure
presentation layer -- computes nothing that harness/scoring.py,
qtree/scoring.py, and examgrade/scoring.py don't already compute; this
script just calls them and plots the output.

Run: `python -m scripts.generate_charts` (writes PNGs into charts/).
Requires matplotlib (dev dependency, not needed to run the benchmark
itself -- see pyproject.toml's dev group).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from harness.scoring import (
    accuracy_table as ct1_8_accuracy_table,
    confidence_at_errors as ct1_8_confidence_at_errors,
    effective_records,
    overall_accuracy as ct1_8_overall_accuracy,
    _manifest_index,
    _truth_for,
)
from harness.spend_ledger import summarize as spend_summarize
from qtree.scoring import (
    confidence_at_local_errors,
    disagreement_at_k10,
    end_to_end_accuracy,
)
from examgrade.scoring import (
    chained_vs_whole_exam_delta,
    confidence_at_errors as ct10_confidence_at_errors,
    with_vs_without_key_delta,
)

CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
SELF_HOSTED_ESTIMATE_PATH = Path(__file__).resolve().parent.parent / "results" / "self_hosted_cost_estimate.json"


def _openjev_self_hosted_by_task() -> dict:
    """OpenJev's real metered spend is $0.00 (free Codiv tier) -- this loads
    the documented estimate of what self-hosting it would actually cost
    (scripts/estimate_self_hosted_cost.py, harness/constants.py's
    SELF_HOSTED_PRICING, methodology.md §17), keyed by task family plus a
    'total' across all three. Charts use this instead of the real $0.00 so
    the cost comparison isn't misleadingly flat -- the OpenJev bar/label is
    styled distinctly (hatched) everywhere this is used, to keep "estimated"
    visually distinct from every other arm's real, measured spend."""
    if not SELF_HOSTED_ESTIMATE_PATH.exists():
        return {"ct1_8": 0.0, "ct9": 0.0, "ct10": 0.0, "total": 0.0}
    data = json.loads(SELF_HOSTED_ESTIMATE_PATH.read_text())
    per_task = data["arms"]["openjev-self-hosted"]
    return {
        "ct1_8": per_task["ct1_8"]["estimated_cost_usd"],
        "ct9": per_task["ct9"]["estimated_cost_usd"],
        "ct10": per_task["ct10"]["estimated_cost_usd"],
        "total": per_task["total"]["estimated_cost_usd"],
    }

# Consistent palette across every chart.
COLOR = {
    "jev": "#2563EB",       # blue -- the subject
    "haiku": "#F59E0B",     # amber -- the reference LLM
    "sonnet": "#7C3AED",    # violet -- the stronger reference LLM (red is reserved
                            # for chart 4's OpenJev Condition-C collapse highlight)
    "openjev": "#10B981",   # green -- the free fallback
    "nli-bart": "#9CA3AF",  # grey -- baseline
    "emb-bge": "#6B7280",   # darker grey -- baseline
}
LABEL = {
    "jev": "Jev",
    "haiku": "Claude Haiku 4.5",
    "sonnet": "Claude Sonnet 5",
    "openjev": "OpenJev",
    "nli-bart": "NLI (bart-large-mnli)",
    "emb-bge": "Embeddings (bge-m3)",
}

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D1D5DB",
        "axes.labelcolor": "#111827",
        "text.color": "#111827",
        "xtick.color": "#374151",
        "ytick.color": "#374151",
        "font.size": 11,
        "font.family": "sans-serif",
        "axes.grid": True,
        "grid.color": "#E5E7EB",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "savefig.dpi": 180,
        "figure.dpi": 100,
    }
)


def _style_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", visible=False)


def _pct(ax) -> None:
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))


def _save(fig, name: str) -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# Chart 1: Part 1 -- shuffle-control collapse (Jev vs NLI/embedding baselines)
# ---------------------------------------------------------------------------
def chart_shuffle_control() -> None:
    arms = ["jev", "nli-bart", "emb-bge"]
    conditions = ["A", "B", "C", "SHUFFLE"]
    cond_labels = ["A: semantic\nnames", "B: opaque\nids", "C: misleading\nnames", "SHUFFLE:\ncontrol"]

    fig, ax = plt.subplots(figsize=(8, 5))
    n_arms = len(arms)
    width = 0.8 / n_arms
    x = range(len(conditions))

    for i, arm in enumerate(arms):
        rows = ct1_8_accuracy_table(arm)
        by_cond: dict[str, list[float]] = {c: [] for c in conditions}
        for r in rows:
            if r.clause_type in (1, 2, 3, 4) and r.condition in by_cond:
                by_cond[r.condition].append(r.accuracy)
        means = [sum(by_cond[c]) / len(by_cond[c]) for c in conditions]
        offsets = [xi + (i - (n_arms - 1) / 2) * width for xi in x]
        ax.bar(offsets, means, width=width * 0.9, label=LABEL[arm], color=COLOR[arm])

    ax.set_xticks(list(x))
    ax.set_xticklabels(cond_labels)
    ax.set_ylim(0, 1.08)
    _pct(ax)
    ax.set_ylabel("Accuracy (CT1-4 average)")
    ax.set_title("Does the model genuinely read the rubric, or match folder-name text?\nJev vs. NLI/embedding zero-shot baselines")
    ax.legend(frameon=False, loc="upper right")
    _style_axes(ax)
    _save(fig, "01_shuffle_control.png")


# ---------------------------------------------------------------------------
# Chart 2: Part 2 -- CT1-4 vs CT5-8 overall accuracy, 3 arms
# ---------------------------------------------------------------------------
def chart_overall_accuracy() -> None:
    arms = ["jev", "haiku", "sonnet", "openjev"]
    groups = ["CT1-4\n(original)", "CT5-8\n(hard mode)"]

    fig, ax = plt.subplots(figsize=(7, 5))
    n_arms = len(arms)
    width = 0.8 / n_arms
    x = range(len(groups))

    for i, arm in enumerate(arms):
        manifest = _manifest_index()
        vals = []
        for cts in [(1, 2, 3, 4), (5, 6, 7, 8)]:
            recs = [r for r in effective_records(arm) if r.clause_type in cts]
            correct = [r.predicted_folder == _truth_for(r, manifest[r.doc_id]) for r in recs]
            vals.append(sum(correct) / len(correct))
        offsets = [xi + (i - (n_arms - 1) / 2) * width for xi in x]
        bars = ax.bar(offsets, vals, width=width * 0.9, label=LABEL[arm], color=COLOR[arm])
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.1%}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels(groups)
    ax.set_ylim(0, 1.08)
    _pct(ax)
    ax.set_ylabel("Overall accuracy")
    ax.set_title("Classification accuracy: original corpus vs. corpus designed to break Jev")
    ax.legend(frameon=False, loc="lower left")
    _style_axes(ax)
    _save(fig, "02_overall_accuracy.png")


# ---------------------------------------------------------------------------
# Chart 3: CT5 arithmetic error rate, 3 arms
# ---------------------------------------------------------------------------
def chart_ct5_arithmetic() -> None:
    arms = ["jev", "haiku", "sonnet", "openjev"]
    manifest = _manifest_index()

    fig, ax = plt.subplots(figsize=(7.5, 5))
    error_rates = []
    for arm in arms:
        recs = [r for r in effective_records(arm) if r.clause_type == 5]
        correct = [r.predicted_folder == _truth_for(r, manifest[r.doc_id]) for r in recs]
        error_rates.append(1 - sum(correct) / len(correct))

    bars = ax.bar([LABEL[a] for a in arms], error_rates, color=[COLOR[a] for a in arms], width=0.6)
    for b, v in zip(bars, error_rates):
        ax.annotate(f"{v:.1%}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=10)
    _pct(ax)
    ax.set_ylabel("Error rate")
    ax.set_title("CT5: arithmetic near a stated threshold\n(the one weakness the vendor's own docs predicted)")
    _style_axes(ax)
    _save(fig, "03_ct5_arithmetic.png")


# ---------------------------------------------------------------------------
# Chart 4: CT7 multi-hop lookup by condition -- OpenJev's and Sonnet's
# isolated Condition-C collapse (misleading-but-plausible folder names)
# ---------------------------------------------------------------------------
def chart_ct7_collapse() -> None:
    arms = ["jev", "haiku", "sonnet", "openjev"]
    conditions = ["A", "B", "C", "SHUFFLE"]
    cond_labels = ["A: semantic", "B: opaque", "C: misleading", "SHUFFLE"]

    fig, ax = plt.subplots(figsize=(8, 5))
    n_arms = len(arms)
    width = 0.8 / n_arms
    x = range(len(conditions))

    for i, arm in enumerate(arms):
        rows = {r.condition: r.accuracy for r in ct1_8_accuracy_table(arm) if r.clause_type == 7}
        vals = [rows[c] for c in conditions]
        offsets = [xi + (i - (n_arms - 1) / 2) * width for xi in x]
        colors = [COLOR[arm]] * len(vals)
        bars = ax.bar(offsets, vals, width=width * 0.9, label=LABEL[arm], color=colors)
        if arm == "openjev":
            bars[2].set_color("#DC2626")  # highlight the Condition-C collapse
            bars[2].set_edgecolor("#7F1D1D")
            bars[2].set_linewidth(1.2)

    ax.set_xticks(list(x))
    ax.set_xticklabels(cond_labels)
    ax.set_ylim(0, 1.08)
    _pct(ax)
    ax.set_ylabel("Accuracy")
    ax.set_title("CT7 multi-hop lookup: misleading names trap OpenJev AND Sonnet\n(both score 100% under opaque SHUFFLE -- a label-collision bug, not a rubric-reading failure)")
    ax.legend(frameon=False, loc="lower left")
    _style_axes(ax)
    _save(fig, "04_ct7_openjev_collapse.png")


# ---------------------------------------------------------------------------
# Chart 5: CT9 -- accuracy by chunk size k, the "smaller steps win" curve
# ---------------------------------------------------------------------------
def chart_ct9_k_curve() -> None:
    arms = ["jev", "haiku", "sonnet", "openjev"]
    k_values = [1, 2, 5, 10]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for arm in arms:
        rows = {(r["k"], r["labeling"]): r["accuracy"] for r in end_to_end_accuracy(arm)}
        ys = [rows[(k, "semantic")] for k in k_values]
        ax.plot(k_values, ys, marker="o", markersize=7, linewidth=2.5, label=LABEL[arm], color=COLOR[arm])

    ax.set_xscale("log")
    ax.set_xticks(k_values)
    ax.set_xticklabels([str(k) for k in k_values])
    ax.set_xlabel("Chunk size k (steps executed per model call)  \u2190 more handoffs        fewer handoffs \u2192")
    _pct(ax)
    ax.set_ylabel("End-to-end accuracy")
    ax.set_title("CT9: chained decision-tree execution\nFrequent small handoffs beat one unassisted full-chain call, for every model")
    ax.legend(frameon=False, loc="upper right")
    _style_axes(ax)
    ax.grid(axis="x", visible=False)
    _save(fig, "05_ct9_k_curve.png")


# ---------------------------------------------------------------------------
# Chart 6: CT10 -- chained vs whole-exam grading accuracy
# ---------------------------------------------------------------------------
def chart_ct10_chained_vs_whole() -> None:
    from examgrade.scoring import question_level_error

    arms = ["jev", "haiku", "sonnet", "openjev"]
    fig, ax = plt.subplots(figsize=(7, 5))
    width = 0.35
    x = range(len(arms))

    chained_vals, whole_vals = [], []
    for arm in arms:
        rows = {(r["mode"], r["with_key"]): r["exact_match_rate"] for r in question_level_error(arm)}
        chained_vals.append((rows[("chained", True)] + rows[("chained", False)]) / 2)
        whole_vals.append((rows[("whole_exam", True)] + rows[("whole_exam", False)]) / 2)

    b1 = ax.bar([xi - width / 2 for xi in x], chained_vals, width=width * 0.9, label="Chained (1 call/question)", color="#93C5FD")
    b2 = ax.bar([xi + width / 2 for xi in x], whole_vals, width=width * 0.9, label="Whole-exam (1 call, all 30)", color="#1E3A8A")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.0%}", (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels([LABEL[a] for a in arms])
    ax.set_ylim(0, 1.12)
    _pct(ax)
    ax.set_ylabel("Grading exact-match rate (avg of with/without key)")
    ax.set_title(
        "CT10: bulk-grading accuracy by architecture\n"
        "Jev's native multi-question call doesn't degrade in bulk mode -- every LLM arm does",
        fontsize=13,
    )
    ax.legend(frameon=False, loc="lower right")
    _style_axes(ax)
    _save(fig, "06_ct10_chained_vs_whole_exam.png")


# ---------------------------------------------------------------------------
# Chart 7: Calibration -- confidence gap (correct - error) across 3 tasks
# ---------------------------------------------------------------------------
def chart_calibration() -> None:
    arms = ["jev", "haiku", "sonnet", "openjev"]
    manifest = _manifest_index()

    def ct5_gap(arm: str) -> float:
        recs = [r for r in effective_records(arm) if r.clause_type == 5 and r.confidence is not None]
        errs = [r.confidence for r in recs if r.predicted_folder != _truth_for(r, manifest[r.doc_id])]
        corr = [r.confidence for r in recs if r.predicted_folder == _truth_for(r, manifest[r.doc_id])]
        if not errs or not corr:
            return float("nan")
        return sum(corr) / len(corr) - sum(errs) / len(errs)

    def ct9_gap(arm: str) -> float:
        c = confidence_at_local_errors(arm)
        return c["at_local_correct"]["mean"] - c["at_local_errors"]["mean"]

    def ct10_gap(arm: str) -> float:
        c = ct10_confidence_at_errors(arm, "chained")
        return c["at_correct"]["mean"] - c["at_errors"]["mean"]

    tasks = ["CT5\n(arithmetic docs)", "CT9\n(chunk execution)", "CT10\n(exam grading)"]
    getters = [ct5_gap, ct9_gap, ct10_gap]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    n_arms = len(arms)
    width = 0.8 / n_arms
    x = range(len(tasks))

    for i, arm in enumerate(arms):
        vals = [g(arm) for g in getters]
        offsets = [xi + (i - (n_arms - 1) / 2) * width for xi in x]
        bars = ax.bar(offsets, vals, width=width * 0.9, label=LABEL[arm], color=COLOR[arm])
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.2f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=9)

    ax.set_xticks(list(x))
    ax.set_xticklabels(tasks)
    ax.set_ylabel("Confidence gap (correct \u2212 error)")
    ax.set_title("Calibration: does confidence actually flag mistakes?\nReplicated on 3 unrelated tasks -- higher is more useful for a review queue")
    ax.legend(frameon=False, loc="upper right")
    _style_axes(ax)
    _save(fig, "07_calibration.png")


# ---------------------------------------------------------------------------
# Chart 8: total cost per arm, whole benchmark (log scale)
# ---------------------------------------------------------------------------
def _arm_totals(use_self_hosted_estimate: bool = False) -> dict:
    spend = spend_summarize()
    totals = {"jev": 0.0, "haiku": 0.0, "sonnet": 0.0, "openjev": 0.0}
    for agg in spend.values():
        source = agg["source"]
        for arm in totals:
            if source.startswith(arm):
                totals[arm] += agg["cost_usd"]
    if use_self_hosted_estimate:
        # OpenJev's real spend above is genuinely $0.00 (free Codiv tier) --
        # swap in the documented self-hosted estimate for reporting, so the
        # cost comparison isn't misleadingly flat. See
        # scripts/estimate_self_hosted_cost.py / methodology.md §17.
        totals["openjev"] = _openjev_self_hosted_by_task()["total"]
    return totals


def chart_cost() -> None:
    totals = _arm_totals(use_self_hosted_estimate=True)
    arms = ["jev", "haiku", "sonnet", "openjev"]
    vals = [max(totals[a], 0.001) for a in arms]  # floor for log scale visibility

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar([LABEL[a] for a in arms], vals, color=[COLOR[a] for a in arms], width=0.6)
    bars[arms.index("openjev")].set_hatch("///")  # estimated, not measured -- see below
    for b, arm in zip(bars, arms):
        if arm == "openjev":
            label = f"~${totals[arm]:.2f} est."
        else:
            label = f"${totals[arm]:.2f}" if totals[arm] >= 0.01 else "$0.00"
        ax.annotate(label, (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom", fontsize=10)
    ax.set_yscale("log")
    ax.set_ylabel("Total spend, whole benchmark (log scale, USD)")
    ax.set_title("Cost across every test (CT1-10 combined)\nJev and a self-hosted OpenJev estimate both cost under 1% of Haiku + Sonnet's spend")
    fig.text(
        0.5, 0.005,
        "OpenJev (hatched): real spend was $0.00 (free hosted tier) -- bar shows the documented self-hosted compute estimate instead",
        fontsize=8, color="#4B5563", ha="center", va="bottom",
    )
    _style_axes(ax)
    _save(fig, "08_cost.png")


# ---------------------------------------------------------------------------
# Chart 9: cost per 1,000 API calls, broken out per test suite
# ---------------------------------------------------------------------------
def chart_cost_per_1000_calls() -> None:
    spend = spend_summarize()
    by_task_arm: dict[tuple[str, str], list[float]] = {}
    task_of_source = {
        "jev_arm": "CT1-8", "haiku_arm": "CT1-8", "sonnet_arm": "CT1-8", "openjev_arm": "CT1-8",
        "jev_arm_ct9": "CT9", "haiku_arm_ct9": "CT9", "sonnet_arm_ct9": "CT9", "openjev_arm_ct9": "CT9",
        "jev_arm_ct10": "CT10", "haiku_arm_ct10": "CT10", "sonnet_arm_ct10": "CT10", "openjev_arm_ct10": "CT10",
    }
    call_counts: dict[tuple[str, str], int] = {}
    for agg in spend.values():
        source = agg["source"]
        if source not in task_of_source:
            continue
        arm = next(a for a in ("jev", "haiku", "sonnet", "openjev") if source.startswith(a))
        task = task_of_source[source]
        per_1000 = agg["cost_usd"] / agg["calls"] * 1000
        by_task_arm[(task, arm)] = per_1000
        call_counts[(task, arm)] = agg["calls"]

    # OpenJev's real per-call cost above is $0.00 (free Codiv tier) -- swap
    # in the documented self-hosted estimate per task family instead, using
    # the same call counts already collected. See
    # scripts/estimate_self_hosted_cost.py / methodology.md §17.
    openjev_est = _openjev_self_hosted_by_task()
    for task, key in (("CT1-8", "ct1_8"), ("CT9", "ct9"), ("CT10", "ct10")):
        calls = call_counts.get((task, "openjev"))
        if calls:
            by_task_arm[(task, "openjev")] = openjev_est[key] / calls * 1000

    tasks = ["CT1-8", "CT9", "CT10"]
    arms = ["jev", "haiku", "sonnet", "openjev"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    n_arms = len(arms)
    width = 0.8 / n_arms
    x = range(len(tasks))

    for i, arm in enumerate(arms):
        vals = [max(by_task_arm.get((t, arm), 0.0), 0.0005) for t in tasks]
        offsets = [xi + (i - (n_arms - 1) / 2) * width for xi in x]
        bars = ax.bar(offsets, vals, width=width * 0.9, label=LABEL[arm], color=COLOR[arm])
        if arm == "openjev":
            for b in bars:
                b.set_hatch("///")
        for b, t in zip(bars, tasks):
            real = by_task_arm.get((t, arm), 0.0)
            if arm == "openjev":
                label = f"~${real:.3f} est."
            else:
                label = f"${real:.3f}" if real >= 0.001 else "$0.00"
            ax.annotate(label, (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom", fontsize=8, rotation=0)

    ax.set_yscale("log")
    ax.set_ylim(top=ax.get_ylim()[1] * 4)  # headroom so the legend never overlaps a bar's annotation
    ax.set_xticks(list(x))
    ax.set_xticklabels(tasks)
    ax.set_ylabel("Cost per 1,000 API calls (log scale, USD)")
    ax.set_title("Price per 1,000 calls, by test suite\nJev and a self-hosted OpenJev estimate both undercut the Claude arms by 15-500x")
    ax.legend(frameon=False, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.0))
    ax.annotate(
        "OpenJev (hatched) = documented self-hosted compute estimate, not the $0.00 free-tier price actually paid",
        xy=(0.5, -0.16), xycoords="axes fraction", fontsize=8, color="#4B5563", ha="center", va="top",
    )
    _style_axes(ax)
    _save(fig, "09_cost_per_1000_calls.png")


# ---------------------------------------------------------------------------
# Chart 10: accuracy vs. cost -- the price/quality comparison quadrant chart
# ---------------------------------------------------------------------------
def chart_accuracy_vs_cost() -> None:
    # CT1-8-specific cost (not the full CT1-10 benchmark total) to match the
    # CT1-8-specific accuracy plotted alongside it.
    spend = spend_summarize()
    ct1_8_sources = {"jev_arm", "haiku_arm", "sonnet_arm", "openjev_arm"}
    totals = {"jev": 0.0, "haiku": 0.0, "sonnet": 0.0, "openjev": 0.0}
    for agg in spend.values():
        if agg["source"] in ct1_8_sources:
            arm = next(a for a in totals if agg["source"].startswith(a))
            totals[arm] += agg["cost_usd"]
    # OpenJev's real CT1-8 spend above is $0.00 -- swap in the documented
    # self-hosted estimate so its point isn't misleadingly pinned to the
    # x-axis floor. See scripts/estimate_self_hosted_cost.py / methodology.md §17.
    totals["openjev"] = _openjev_self_hosted_by_task()["ct1_8"]

    arms = ["jev", "haiku", "sonnet", "openjev"]

    manifest = _manifest_index()
    accs = {}
    for arm in arms:
        recs = effective_records(arm)
        correct = [r.predicted_folder == _truth_for(r, manifest[r.doc_id]) for r in recs]
        accs[arm] = sum(correct) / len(correct)

    fig, ax = plt.subplots(figsize=(7.5, 6))
    for arm in arms:
        x_val = max(totals[arm], 0.001)
        # Haiku and Sonnet land close together on both axes (similar accuracy,
        # similar log-scale cost) -- push Sonnet's label below its point so
        # the two annotations don't overlap. OpenJev's estimated cost now
        # lands close to Jev's on the x-axis and low enough on the y-axis to
        # collide with the "97.0%" gridline label when placed above -- push
        # it below too.
        y_offset = -34 if arm == "sonnet" else (-62 if arm == "openjev" else 22)
        va = "bottom" if y_offset > 0 else "top"
        marker_kwargs = (
            {"facecolor": "none", "edgecolor": COLOR[arm], "linewidth": 2.5, "hatch": "///"}
            if arm == "openjev"
            else {"color": COLOR[arm], "edgecolor": "white", "linewidth": 1.5}
        )
        ax.scatter([x_val], [accs[arm]], s=420, zorder=3, **marker_kwargs)
        arm_label = f"{LABEL[arm]} (self-hosted est.)" if arm == "openjev" else LABEL[arm]
        cost_label = f"~${totals[arm]:.2f} est." if arm == "openjev" else f"${totals[arm]:.2f} total"
        ax.annotate(
            f"{arm_label}\n{accs[arm]:.1%} accuracy, {cost_label}",
            (x_val, accs[arm]),
            textcoords="offset points",
            xytext=(0, y_offset),
            ha="center",
            va=va,
            fontsize=10,
            fontweight="bold",
        )

    ax.set_xscale("log")
    ax.set_xlabel("Total cost, all 5,760 CT1-8 classifications (log scale, USD)  \u2192 more expensive")
    _pct(ax)
    ax.set_ylabel("CT1-8 overall accuracy  \u2191 more accurate")
    ax.set_title("Accuracy vs. cost in one chart\nTop-left wins: cheaper AND more accurate")
    ax.set_ylim(min(accs.values()) - 0.03, 1.02)
    _style_axes(ax)
    _save(fig, "10_accuracy_vs_cost.png")


if __name__ == "__main__":
    chart_shuffle_control()
    chart_overall_accuracy()
    chart_ct5_arithmetic()
    chart_ct7_collapse()
    chart_ct9_k_curve()
    chart_ct10_chained_vs_whole()
    chart_calibration()
    chart_cost()
    chart_cost_per_1000_calls()
    chart_accuracy_vs_cost()
    print("done")
