# Methodology — Rubric-Based Zero-Shot Classification Model Benchmark

Living document. Updated as each phase of [`test-plan.md`](./test-plan.md) is
built. This file records *decisions actually made*, including anywhere
implementation diverged from the original design and why. `results.md` holds
the numbers; this file holds how they were produced.

Status: **Phase 0 (scaffold) complete. Phase 1 (corpus + ground truth) complete.**

---

## 0. Product verification

Before building against it, the following was confirmed live (2026-09-21):

- `typesafe.ai` / `docs.typesafe.ai` — Jev is a real, shipping product.
  Endpoint `POST https://api.typesafe.ai/v1/systemone`, model `jev-1.13.0`
  (alias `jev-latest`), $42/Btok input ($0.042/Mtok), output tokens free,
  64k context. PyPI package `typesafe-sdk` (0.7.1 as installed here).
- `razorback16/openjev` — real, 284 GitHub stars. Speaks Jev's wire API.
  Requires a 24GB-class GPU for local self-hosting (NVFP4 DiffusionGemma
  26B-A4B); **not runnable on this machine's RTX 3050 8GB**. Used instead
  via the free-hosted `api.codiv.ai` endpoint (same `typesafe-sdk` client,
  different `base_url` and model name).
- `zhuyansen/jev-zeroshot-vs-bert` — real published harness (MIT), used as a
  methodology reference for bootstrap CIs and paired-bootstrap deltas, not
  forked directly (different task shape: rubric-conditioned sorting, not
  public zero-shot classification datasets).
- Claude Haiku 4.5 pricing confirmed via `platform.claude.com/docs`: $1/Mtok
  input, $5/Mtok output (standard, non-batch).

## 1. Randomization

Every choice that should be uninfluenced by semantics (per user instruction)
uses Python's `random.Random` seeded explicitly, never the global RNG state,
so each stream is independently reproducible.

| Purpose | Seed source | Where |
|---|---|---|
| Opaque folder IDs (Condition B) | `MASTER_SEED ^ "folder_ids"` | `rubrics/conditions.py` |
| Shuffle-control permutation | `MASTER_SEED ^ "shuffle_control"` | `rubrics/shuffle_control.py` |
| Validation/test split assignment | `MASTER_SEED ^ "split"` | `corpus/generate.py` |
| Corpus template/variant/entity selection | `MASTER_SEED ^ "corpus"` | `corpus/generate.py` |
| Run-time document ordering per arm | `MASTER_SEED ^ "run_order"` | `harness/runner.py` |

`MASTER_SEED = 20260921` (date this benchmark was drafted, per test-plan.md's
own "Drafted 2026-09-21"), recorded once in `harness/constants.py`. Each
purpose XORs a distinct string-derived integer against it so streams cannot
collide, and every generation script logs its resolved seed into the
artifact it produces (`corpus/manifest.jsonl`, `results/runs/*.json`) for
audit.

## 2. Corpus methodology (§5.3 independence control)

Per test-plan.md §5.3, ground truth must be computed independently of rubric
wording. Implementation:

1. **Structured metadata generated first**, before any rubric clause text
   exists in code: document type, dollar amount, parent-project id (or
   none), retainer-client membership (or none), superseded flag. This lives
   in `corpus/manifest.jsonl` and is the sole source of ground truth.
2. **Ground truth is a pure function** `rubrics/ground_truth.py:
   correct_folder(metadata, clause_type, condition) -> folder_id`, unit
   tested, that never reads document prose — only the structured fields.
3. **Prose is generated after metadata is frozen**, using **Claude Sonnet 5**
   (not Haiku) specifically to avoid a self-consistency confound: Haiku is
   one of the arms under test, and using Haiku to author the documents Haiku
   later classifies would risk giving that arm a home-field advantage in
   phrasing legibility. This is a deliberate deviation from "no LLM in
   corpus generation" toward "LLM in corpus generation, but never the LLM
   being scored."
4. Folder-name conditions (A/B/C) and the shuffle-control permutation are
   applied as a final, separate layer on top of the frozen corpus — the same
   600+ documents are reused across all three conditions, only the
   folder-name mapping changes.

## 3. Decomposition commitment (§8 known confound)

One `Choice` question per document, full rubric text passed as `criteria`
per folder option, document content as `state`. Applied identically across
every arm, including Haiku (same rubric text, constrained JSON output
`{folder_id, confidence}`, temperature 0). Fixed before any tuning pass, not
varied per condition or clause type.

## 4. Equal-effort budget (§5.2)

TBD — logged once the pilot/tuning pass (Phase 7) runs. Will record: number
of tuning iterations per arm, what changed each iteration, and the frozen
validation-split accuracy at cutoff.

## 5. Cost and latency logging

Every arm implementation (`arms/*.py`) returns a common `Prediction` object
carrying `latency_ms` and provider-reported token usage (or none, for local
arms). `harness/cost.py` converts usage to USD using the rates in this file
(re-verified at run time where the provider exposes a `usage` field, so
actual spend — not list price — is what's reported in `results.md`).

| Arm | Rate basis |
|---|---|
| `jev` | $0.042/Mtok input, output free (per `usage.input_tokens`) |
| `openjev` (Codiv) | free tier (100M input tokens); logged as $0 with a note |
| `haiku` | $1/Mtok input, $5/Mtok output |
| `nli-bart`, `emb-bge` | $0 (local CPU/GPU compute; wall-clock logged instead) |

## 6. Known deviations from test-plan.md

- **Corpus is shared across conditions, not regenerated per condition.**
  test-plan.md §2 frames A/B/C as "three folder-naming conditions over the
  same corpus and the same rubric," which is what's implemented: 240 unique
  documents (200 test + 40 validation, 50/10 per clause type), each scored
  under all three folder-name conditions plus the shuffle control. §3's "50
  documents per clause type per condition" is satisfied as 50 *evaluations*
  per (clause type × condition) cell, not 50 independently-generated
  documents per cell -- generating physically different documents per
  condition would violate §5.3 (conditions must differ only in folder
  naming, not in content) and would 3x corpus-generation cost for no
  methodological benefit.
- Otherwise none yet.

## 7. Corpus generation results (Phase 1 actual)

- 240 documents generated: 4 clause types × (50 test + 10 validation).
- Metadata (Stage A, `corpus/generate_metadata.py`) is free -- pure
  stratified sampling, no API calls. Verified canonical-folder distribution
  after generation: CT1 16/17/17 (tax/invoices/contracts), CT2 25/25
  (large/small, ~30% of each near the $10k boundary), CT3 17/16/17
  (project_one/project_two/retainer_clients, with non-retainer docs getting
  a 50%-chance non-retainer-client distractor name so "any client name
  present" is never a valid shortcut), CT4 25/25 (active/superseded).
- Prose (Stage B, `corpus/generate_prose.py`) used `claude-sonnet-5`
  (confirmed exact API model id via `GET /v1/models` on 2026-09-21 --
  distinct from and cheaper than `claude-sonnet-4-5`/`claude-sonnet-4-6`).
  Batched 8 documents per call, delimiter-parsed. Total: 31 calls, 41,408
  input / 97,588 output tokens, **$1.0587** logged. $3.94 of the $5.00
  Anthropic budget remains for the Haiku arm and any tuning passes.
- Manual spot-check of 6 documents across all 4 clause types confirmed the
  required load-bearing facts are present and unambiguous in the prose
  (exact dollar figures for CT2, explicit project-name + client-name
  mentions for CT3 including a correctly-distinguished non-retainer
  near-miss name, explicit supersession language for CT4), with no
  leakage of rubric/meta language ("this document belongs in...") into the
  text itself.
- Operational note: the first full-corpus generation run was killed by the
  harness's own 10-minute command timeout (stdout was fully buffered
  because output was piped, not a subprocess crash); `generate_prose.py`
  skips documents that already have a file on disk, so the run resumed
  cleanly with `python -u` (unbuffered) and no wasted spend or duplicate
  documents.
- **Environment gotcha:** `ANTHROPIC_API_KEY` must be read from `.env` via
  `harness/env.py` (`python-dotenv`, `override=True`), not from the ambient
  shell environment -- an earlier, invalidated key was persisting in the
  tool session's inherited shell env and caused a false 401 before this was
  diagnosed.
