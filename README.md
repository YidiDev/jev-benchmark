# Rubric-Based Zero-Shot Classification Model Benchmark

Does Jev evaluate a multi-clause rubric over file content in a way that
NLI-based zero-shot classification structurally cannot — and does it match a
cheap LLM (Claude Haiku 4.5) on quality?

Full design: see [`test-plan.md`](./test-plan.md). Running log of decisions,
corpus/prompt methodology, and price/quality results: see
[`methodology.md`](./methodology.md) and [`results.md`](./results.md).

Status: in progress. See `results.md` for the latest numbers.

## Setup

```bash
uv sync
cp .env.example .env   # fill in TYPESAFE_API_KEY, ANTHROPIC_API_KEY, CODIV_API_KEY
```

## Layout

```
corpus/     document generator + frozen manifest + ground-truth engine
rubrics/    rubric clause text, folder-name conditions, shuffle-control permutation
arms/       one module per arm: jev, openjev, nli-bart, emb-bge, haiku
harness/    runner, scoring (bootstrap CI, ECE, disagreement), cost/latency, report
results/    raw run JSON + rendered tables
scripts/    pilot.py (small smoke test), run_all.py (full experiment)
```

## Run

```bash
python -m scripts.pilot      # small validation-split smoke test, all arms
python -m scripts.run_all    # full 3-repeat run, all arms x conditions x clause types
```
