# AGENTS.md

## What this is
A research benchmark comparing a rubric-classification model (Jev) against Claude
Haiku/Sonnet, OpenJev, and NLI/embedding baselines across 10 test suites (CT1-CT10:
document sorting, chained decision-tree execution, exam grading). Not a typical app —
treat `results/`, `corpus/*/documents/`, and `charts/` as committed data artifacts, not
scratch output.

Full narrative docs (read before re-deriving anything): `README.md` (summary + repro
commands), `test-plan.md` (pre-registered design), `methodology.md` (decision log, why
things are built the way they are, 17 sections), `results.md` (full numeric results).

## Setup & tests
- Package manager is `uv`. Install: `uv sync`.
- Run tests: `uv run pytest tests/ -q` (124 tests, ~30s, **no API keys or network
  needed** — everything under test is pure/local logic). `testpaths = ["tests"]` is set
  in `pyproject.toml`, so bare `pytest` also targets the right dir.
- No lint/typecheck/formatter/pre-commit/CI is configured in this repo. Don't invent one.
- `.env` (copy from `.env.example`) only needed to actually *run* an arm against a live
  API (`TYPESAFE_API_KEY`, `ANTHROPIC_API_KEY`, `CODIV_API_KEY`/`CODIV_BASE_URL`) — never
  needed for the test suite.

## Repo layout
- `corpus/` — CT1-8 document generator + frozen `manifest.jsonl` + ground-truth engine.
- `rubrics/` — rubric clause text, folder-name conditions (A/B/C + SHUFFLE), the
  shuffle-control permutation.
- `arms/` — one module per CT1-8 model arm (`jev`, `haiku`, `sonnet`, `openjev`,
  `nli-bart`, `emb-bge`), common interface in `arms/base.py` (`Arm.predict(doc_text,
  rubric) -> Prediction`).
- `qtree/` — CT9 (chained decision-tree execution): tree def, chunked arms, scoring.
- `examgrade/` — CT10 (exam grading): questions/rubrics, student corpus, grading arms.
- `harness/` — shared scoring (bootstrap CI, ECE, disagreement), spend ledger,
  `constants.py` (seeds, pricing, budgets), `env.py` (.env loader).
- `scripts/` — `run_arm.py`/`run_api_arm.py` (CT1-8), `generate_summary.py`,
  `generate_charts.py`, `estimate_self_hosted_cost.py`.
- `results/`, `charts/` — committed outputs, regenerable via the scripts above.

## Running arms (all resumable — safe to rerun, skips already-written predictions)
```bash
python -m scripts.run_arm --arm nli-bart      # local deterministic arms, no --repeats
python -m scripts.run_api_arm --arm jev       # or haiku / sonnet / openjev
python -m qtree.runner --arm jev              # CT9
python -m examgrade.runner --arm jev          # CT10
```
Debug flags: `--limit N` (first N manifest rows), `--repeats 1` (skip multi-repeat), on
most runners.

## Hard constraints — do not violate
- **Every paid API call must go through `harness.spend_ledger.record_spend`.** It
  enforces `ANTHROPIC_BUDGET_USD` (`harness/constants.py`) and raises `BudgetExceeded`
  before the budget would be crossed. Never bypass this when adding/editing an arm.
- **Real spend vs. self-hosted cost estimates are separate and must not be mixed.**
  `results/spend_ledger.jsonl` (via `PRICING`) is real, metered spend. `SELF_HOSTED_PRICING`
  / `estimated_self_hosted_cost()` is a documented, clearly-labeled projection — it is
  never written to the ledger and never counted against the budget.
- **Never use the bare `random` module.** Always `harness.constants.sub_rng(purpose)`
  for reproducible, independently-auditable RNG streams (seeded off `MASTER_SEED`).
- **SHUFFLE condition handling differs by arm type, deliberately**: local arms
  (nli-bart/emb-bge) reuse Condition B predictions for SHUFFLE scoring
  (`ARMS_SYNTHESIZE_SHUFFLE_FROM_B` in `harness/predictions.py`) because they never see
  rubric text. API arms (jev/haiku/sonnet/openjev) must run SHUFFLE as a real, separate
  condition — the rubric *text* differs for them. Getting this backwards silently
  invalidates the shuffle-control result (see `tests/test_run_api_arm.py` and
  `methodology.md` §8).
- **Haiku intentionally runs at `REPEATS=2`**, not the global `REPEATS=3` default — a
  documented, budget-driven exception (`arms/haiku.py`). Don't "fix" it to match the
  constant.
- **Corpus documents are frozen, committed artifacts.** Regenerating them
  (`corpus/generate_metadata.py` → `corpus/generate_prose.py`, and the `qtree`/`examgrade`
  equivalents) costs real Anthropic API money (Sonnet authors the prose) and is never
  required to run tests or reproduce existing results.
- Import `harness.env` (or anything that transitively imports it) before reading any API
  key env var — it loads `.env` with `override=True`, avoiding stale shell-env values.
