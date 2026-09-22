# Methodology — Rubric-Based Zero-Shot Classification Model Benchmark

Living document. Updated as each phase of [`test-plan.md`](./test-plan.md) is
built. This file records *decisions actually made*, including anywhere
implementation diverged from the original design and why. `results.md` holds
the numbers; this file holds how they were produced.

Status: **Phase 0 (scaffold) complete. Phase 1 (corpus + ground truth) complete.
Phase 2 (local baseline arms nli-bart, emb-bge) complete. Phase 3 (Jev arm,
full 3-repeat run including shuffle control) complete. Phase 4 (Haiku arm,
full 3-repeat run) complete. "Hard mode" clause types CT5-CT8 (§12) complete
for all four built arms (jev, haiku, nli-bart, emb-bge), full 3-repeat scope.
Phase 6 (scoring harness: bootstrap CI, ECE, shuffle delta, disagreement,
cost/latency) built and used to produce the numbers below.**

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

## 8. Arm interface (all five arms implement this)

`arms/base.py` defines the common contract: `Arm.predict(doc_text: str,
rubric: Rubric) -> Prediction`, where `Prediction` carries `folder`,
`probabilities` (dict, folder display name -> score), `confidence`,
`latency_ms`, and (for token-metered API arms only) `input_tokens` /
`output_tokens`. Every arm receives the exact same `Rubric` object from
`rubrics.clauses.build_rubric(clause_type, condition)` and the exact same
document text -- no per-arm prompt/rubric variation.

`harness/predictions.py` defines the shared on-disk record format
(`PredictionRecord`) and one JSONL file per arm at
`results/predictions/{arm}.jsonl`. Runners are resumable: `existing_keys(arm)`
returns the `(doc_id, condition, repeat)` triples already recorded, so an
interrupted run (or a deliberate re-run after fixing a bug) never
re-predicts or, for paid arms, double-bills.

**Condition SHUFFLE is never run as its own condition.** The shuffle control
(test-plan.md §5.1) shows the model the *same opaque-id folder set* as
Condition B -- only the scoring-time answer key differs (a permuted
clause-to-id mapping instead of the true one). Since the model only ever
sees folder ids and document text, re-running under SHUFFLE would be
identical work for identical output. `harness/scoring.py` (Phase 6) will
synthesize shuffle-control accuracy directly from each arm's Condition B
records via `rubrics.ground_truth.correct_folder(metadata, shuffle=True)`.

**Repeats.** Local deterministic arms (nli-bart, emb-bge: no sampling
temperature, pure argmax over a fixed forward pass) are run once
(`repeat=1`) -- re-running a deterministic computation produces
byte-identical output and adds no statistical information. Stochastic API
arms (jev, haiku, openjev) will use `REPEATS=3` from `harness/constants.py`
per test-plan.md's run-to-run variance requirement, which explicitly
includes Haiku at temperature 0 (still non-deterministic in practice).

## 9. Local baseline arms (Phase 2 actual)

- **`nli-bart`** (`arms/nli_bart.py`): HF `zero-shot-classification` pipeline,
  `facebook/bart-large-mnli`, `candidate_labels=rubric.folders`,
  hypothesis template `"This document should be filed in the folder called
  {}."`. Deliberately never sees `rubric.criteria`/`instructions` -- an NLI
  zero-shot pipeline has no mechanism to consume a rubric, only label text,
  which is exactly the property test-plan.md §3 wants isolated.
- **`emb-bge`** (`arms/emb_bge.py`): `sentence-transformers`,
  `BAAI/bge-m3`, cosine similarity between the document embedding and each
  folder display name's embedding (label text only, same reasoning as
  above). `probabilities` is a temperature-1 softmax over raw cosine
  similarities for reporting only -- per test-plan.md §6, ECE/calibration is
  only computed for jev/openjev/haiku, not this arm, so no calibration claim
  is made for these softmax values.
- Both ran via `python -m scripts.run_arm --arm <name>` (generic runner,
  `scripts/run_arm.py`) over the full 240-document manifest × 3 conditions =
  720 predictions each, zero API cost (local GPU, RTX 3050 8GB). nli-bart:
  111.6s wall clock (first call includes one-time model load). emb-bge:
  44.0s wall clock.
- **Sanity-check accuracy** (against ground truth, full 240-doc corpus × 3
  conditions, before any bootstrap CI / formal scoring harness -- Phase 6
  will produce the real numbers for results.md):

  | Clause type | nli-bart A | nli-bart B | nli-bart C | emb-bge A | emb-bge B | emb-bge C |
  |---|---|---|---|---|---|---|
  | CT1 descriptive | 1.00 | 0.30 | 0.00 | 0.77 | 0.35 | 0.07 |
  | CT2 conjunctive+threshold | 0.65 | 0.57 | 0.35 | 0.53 | 0.37 | 0.47 |
  | CT3 relational | 0.37 | 0.37 | 0.28 | 0.47 | 0.32 | 0.22 |
  | CT4 negative/exclusionary | 0.58 | 0.50 | 0.42 | 0.52 | 0.50 | 0.48 |

  This matches the design's expectation exactly: CT1 (where the folder
  display name alone is a near-perfect proxy for content) is where both
  instruments do best on Condition A (nli-bart hits a perfect 1.00) and
  collapse hardest on B (near chance, 1/3 ≈ 0.33) and C (actively *worse*
  than chance -- 0.00 for nli-bart -- because Condition C's labels are the
  same semantic strings as A, just deranged onto the wrong folders, so a
  label-text matcher confidently picks the *wrong* one). Verified directly:
  for every document, nli-bart and emb-bge produce the *identical*
  prediction under Condition A and Condition C, since both conditions show
  the model the same set of display strings (`{tax, invoices, contracts}`)
  and only the correct-answer key differs between them -- exactly the
  artifact-detection mechanism test-plan.md §5.1 is designed around, now
  confirmed working end-to-end on real (non-Jev) models before any paid API
  call has been made.

## 10. Jev arm (Phase 3 actual)

`arms/jev.py`: official `typesafe-sdk`, `TypeSafeClient(model="jev-latest")`,
one `Choice` question per document (`instructions`/`criteria` from
`rubrics.clauses.build_rubric`, `state` = raw document text). Every call
logged via `harness.spend_ledger.record_spend`.

### Incident: the shuffle-control reuse shortcut was wrong for rubric-reading arms

Phase 2's design decision -- "SHUFFLE reuses Condition B's predictions,
never run separately" -- is **only valid for nli-bart/emb-bge**. Those arms
only ever see the folder-id *set* as candidate labels, and Condition B and
SHUFFLE present the identical set (SHUFFLE is just a different assignment of
*which* id is correct), so the model's chosen label string is provably
identical between the two.

Jev is handed the *full rubric text*, and that text is genuinely different
between B and SHUFFLE: `build_rubric(ct, "SHUFFLE")` formats the same rule
template with a permuted canonical-id → display-name mapping, e.g. for CT1,
Condition B says `"Tax documents go to `w1tqk1`. Invoices go to `fh4pr2`.
Contracts go to `c52z16`."` while SHUFFLE says `"Tax documents go to
`fh4pr2`. Invoices go to `c52z16`. Contracts go to `w1tqk1`."` for the exact
same opaque-id set. The first full Jev run only queried A/B/C and then
scored Condition B's answers against the *shuffled* answer key, which is
mathematically guaranteed to read ~0% whenever the model is in fact
following the true rubric (a derangement has zero fixed points, so 100%
accuracy under the true mapping implies ~0% under any relabeling of the
same answers) -- this produced a false "Jev fails the shuffle control"
signal that was caught by manual inspection before being written to
results.md, not by an automated check.

**Fix**: `scripts/run_api_arm.py` now iterates
`API_ARM_CONDITIONS = ("A", "B", "C", "SHUFFLE")` for all three API arms
(jev, haiku, openjev), genuinely querying the model under the shuffled
rubric text. `scripts/run_arm.py` (local arms) is unchanged -- SHUFFLE reuse
remains correct and is now explicitly justified in both runners'
docstrings. A regression test
(`tests/test_run_api_arm.py::test_shuffle_rubric_text_differs_from_condition_b`)
asserts the instructions text differs between B and SHUFFLE for every
clause type, so this class of bug cannot silently reappear.

### Full run results (2,880 predictions: 240 docs × 4 conditions incl. SHUFFLE × 3 repeats)

**Accuracy is 1.00 (180/180) in every single (clause_type × condition) cell,
including SHUFFLE.** Manually verified against ground truth on several
targeted hard cases to rule out a scoring bug:

- CT2 "hard" near-threshold amounts ($10,424.97, $10,518.52, both just above
  the $10,000 line; $8,600.77, just below) -- all correctly bucketed,
  confidence 1.0.
- CT3 retainer-override cases with a *distractor* project codename present
  in the same document (e.g. project=Alpha, client="Beacon Systems" — a
  retainer client — correctly routed to `retainer_clients` despite the
  competing project-based signal) -- all correct, confidence 0.99–1.0.

**Interpretation**: this is a genuine ceiling effect, not a bug. Jev
resolves every clause type in this corpus perfectly, including the ones
test-plan.md §3 and the jev-1.13 jaggedness doc predicted would be hardest
(CT2's numeric threshold, CT3's relational/multi-hop lookup). Two
non-exclusive readings, to be revisited once Haiku's numbers exist for
comparison: (a) Jev is simply very capable at this exact decomposition
(one Choice question, full rubric in criteria, moderate document length);
(b) this corpus's "hard" cases are still fully explicit in the text (CT2
states the exact dollar figure as required by `corpus/prose_prompts.py`, so
it is a text-comparison task, not true arithmetic/estimation) and may not
be adversarial enough to separate Jev from a strong LLM. The 100%
shuffle-control result is the more decision-relevant one regardless: it
directly answers Part 1 of test-plan.md -- Jev's accuracy tracks the
*stated* rubric mapping even when it is adversarially permuted away from
the semantically "obvious" answer, which is the specific signature of
genuine rubric-conditioning rather than content-prior matching.

**Cost**: 2,880 calls, well under $0.10 total logged spend (see
`results/spend_ledger.jsonl` for the exact running total via
`python -m harness.spend_ledger`); output tokens are free under Jev's
pricing. Wall clock: ~576s combined across both runner invocations (first
A/B/C pass + the SHUFFLE-only resumption pass after the fix above).

## 11. Haiku arm (Phase 4 actual)

`arms/haiku.py`: official `anthropic` SDK, `claude-haiku-4-5-20251001`,
forced tool-use (`tool_choice={"type":"tool","name":"choose_folder"}`) for
constrained `{folder_id, confidence}` output, `folder_id` drawn from an
explicit enum matching `rubric.folders` (structurally mirroring Jev's
`Choice` primitive -- Haiku cannot answer with a nonexistent folder any more
than Jev can). Same rubric text as every other arm (instructions + criteria
descriptions), document text appended after it in the user message.

**Deviation from test-plan.md's "temp 0":** the live Messages API for this
account has no `temperature` parameter at all (confirmed via the SDK's
`Messages.create` signature and `platform.claude.com/docs/en/api/messages`
on 2026-09-21) -- superseded by `output_config.effort`
(low/medium/high/xhigh/max), which controls reasoning depth, not sampling
randomness. There is no lower-variance mode to opt into; every call runs at
the API's default sampling behavior. This makes the run-to-run variance
metric even more load-bearing than test-plan.md anticipated: it's the only
axis of non-determinism available, not a residual one on top of temp 0.

### Cost problem and resolution

A pre-flight cost projection from a real 8-call sample (avg 1,228 input /
56.5 output tokens/call) put the full test-plan.md-specified run (3 repeats
x 4 conditions incl. SHUFFLE x 240 docs = 2,880 calls) at roughly **$4.35**,
against a **$3.93** remaining Anthropic budget at the time -- short by about
$0.42 even before accounting for smoke-test spend already incurred.

**Prompt caching was tried and found ineffective for this model.** The
rubric-dependent content (system prompt + rubric text + tool schema) shared
across all documents in one (clause_type, condition) pair is only
~900-1,000 tokens, but **Claude Haiku 4.5's documented minimum cacheable
prompt length is 4,096 tokens**
(`platform.claude.com/docs/en/build-with-claude/prompt-caching#cache-limitations`,
confirmed 2026-09-21) -- far above what this arm has available to cache.
Confirmed empirically: `cache_creation_input_tokens` and
`cache_read_input_tokens` both came back 0 on real test calls with
`cache_control` set on the system block and tool definition. Padding the
prefix with ~3,000 tokens of meaningless filler to clear the threshold was
considered and rejected -- it would save only ~$1.30 while materially
harming the "fair fight" realism of the reference arm's context. (The
cache-aware fields added to `harness/spend_ledger.py` and
`arms/base.Prediction` during this investigation were kept -- they're
harmless at 0 and could benefit a future arm/model with a lower cache
minimum -- but they are always 0 for this arm.)

**Actual fix: `REPEATS=2` for this arm instead of 3.** A deliberate,
documented scope reduction, not a silent one -- test-plan.md specifies 3
repeats for the run-to-run variance metric. What's preserved in full: all 4
conditions (A/B/C/SHUFFLE) and both splits (240 docs), which is what the
two decision-relevant Part 2 metrics (per-condition accuracy, shuffle
tracking) need. What's reduced: statistical power on the one secondary
metric (run-to-run disagreement rate), from 3 repeats to 2. Cost at 2
repeats: 1,920 calls, projected ~$2.90, comfortably inside budget.

### Full run results (1,920 predictions: 240 docs × 4 conditions incl. SHUFFLE × 2 repeats)

**Overall accuracy: 1,875/1,920 = 97.66%**, against Jev's 100% on the
identical corpus/conditions (§10). Haiku genuinely underperforms Jev on
this benchmark.

| Clause type | A | B | C | SHUFFLE |
|---|---|---|---|---|
| CT1 descriptive | 1.00 | 1.00 | 0.97 | 1.00 |
| CT2 conjunctive+threshold | 1.00 | 1.00 | 0.98 | 1.00 |
| CT3 relational | 0.93 | 0.93 | 0.93 | 0.92 |
| CT4 negative/exclusionary | 1.00 | 1.00 | 0.98 | 1.00 |

**Error concentration: 37 of 45 total errors (82%) are in CT3**, and every
single one of those 37 has the *same* mechanism: the document's
`mentioned_client` is a non-retainer distractor company name that happens
to share a prefix word with a real retainer-list client (both were drawn
from the same prefix/suffix word bank in `rubrics/clause_specs.py`'s
`CT3_FIXTURES`, by design -- see methodology.md §1's CT3 fixture generation
for the word banks). For example: distractor "Anchor Robotics" confused for
retainer "Anchor Materials"; distractor "Beacon Foundry" confused for
retainer "Beacon Systems"; distractor "Lattice Dynamics" confused for
retainer "Lattice Capital". Haiku is confidently wrong on these (confidence
0.95-1.00 on every misclassified case checked), suggesting it is matching
on the shared prefix token rather than checking the full company name
against the stated retainer list -- exactly the kind of near-miss
relational lookup test-plan.md §3 (clause type 3) and the jev-1.13
jaggedness doc both flagged as the expected hard case, except here it's
Haiku, not Jev, that fails it. Jev handled the identical documents (e.g.
`ct3_te_011`, `ct3_te_007`) correctly in §10's manual spot-checks. The
remaining 8 errors (CT1/CT2/CT4, all under Condition C) are isolated
misleading-condition slips with no obvious shared mechanism.

**Run-to-run disagreement** (repeat 1 vs repeat 2, same doc+condition):
7/960 = 0.73%. Small but nonzero, confirming Haiku is not perfectly
deterministic even with no temperature control exposed, as anticipated.

**Cost**: 1,934 total logged Haiku calls (1,920 production + smoke tests),
$2.8804 for this arm; cumulative Anthropic spend $3.9391 / $5.00 budget,
**$1.0609 remaining**. See `results/spend_ledger.jsonl` for exact figures.

### Sonnet comparison: raised, then explicitly declined by the user

Per prior user instruction ("if haiku underperforms jev, ask for more
budget to test with sonnet"), Haiku's underperformance here (97.66% vs
100%) was flagged along with a cost projection for a comparable Sonnet 5
run (~$5.72 at repeats=2, ~$8.58 at repeats=3, since Sonnet 5 is priced at
exactly 2x Haiku 4.5's per-token rates -- would have required raising the
Anthropic budget). **User's decision: skip it.** Verbatim: "if jev did
100%, not worth testing the other stuff. that's insanely good." Rationale
accepted as sound -- a clean 100% ceiling with a genuine, mechanistically-
understood 2.34-point gap to a strong reference LLM (concentrated 82% in
one clause type, with a specific, identified failure mode) is already a
decisive result under test-plan.md §6's decision rule ("Jev >= Haiku on
accuracy -> adopt"); a third model doesn't change that conclusion, and
$1.06 of the original $5.00 Anthropic budget remains unspent as a result.
No Sonnet arm was built. Phase 5+ proceeds with the four arms actually
built (jev, haiku, nli-bart, emb-bge) plus openjev once/if
`CODIV_API_KEY` arrives, per the original lowest-priority plan.

### Addendum: Haiku's 3rd repeat completed (as a side effect of §12's budget increase)

When the Anthropic budget was raised to fund CT5-CT8 (§12), `scripts.run_api_arm
--arm haiku` was re-run without a `--repeats` override, which defaults to
`REPEATS=3` from `harness/constants.py` -- this transparently filled in
Haiku's missing 3rd repeat for CT1-4 as well (960 additional calls), not
just CT5-8's. Not originally budgeted for, but a welcome bonus: CT1-4 now
matches test-plan.md's specified 3 repeats exactly, same as Jev. Updated
CT1-4 numbers with the 3rd repeat included: overall accuracy 2,815/2,880 =
**97.74%** (vs. 97.66% at 2 repeats -- a negligible shift, confirming the
2-repeat numbers above were already a stable estimate). Per-clause-type:
CT1 99.31%, CT2 99.58%, CT3 92.36%, CT4 99.72%. The qualitative story is
identical to the 2-repeat analysis above: of 65 total CT1-4 errors, 55
(85%) are CT3, the same prefix-matching mechanism. See `results.md` Part 2
for the final, 3-repeat-authoritative tables.

## 12. Hard mode: CT5-CT8

### Motivation

CT1-4 turned out to be a ceiling task for Jev: 100.00% across every
condition and the shuffle control (§10). That answers test-plan.md's
"does Jev genuinely condition on the rubric" question cleanly, but it
cannot answer "where does Jev actually break" -- a benchmark that never
observes a failure can't characterize one. User instruction: "it's not
worth much if jev is perfect at our test. we need to find its limits."

Rather than making CT1-4 harder (which would have retroactively
invalidated the already-committed, expensive Haiku comparison), four new
clause types were added, each isolating exactly one documented jev-1.13
weakness (`docs.typesafe.ai/model-jaggedness/jev-1.13`) **in isolation**,
so a drop in accuracy is attributable to a single cause rather than a
tangle of them:

| Type | Targets | Design | Contrast with existing type |
|---|---|---|---|
| CT5 computed_threshold | "bad at math/counting" | Document lists 2-5 line items, states no total; rubric requires summing and comparing to a $5,000 threshold | CT2 states a single total explicitly -- text comparison, not arithmetic |
| CT6 temporal_reasoning | "bad at date/time ordering" | Document states two dates (its own effective date + a related version's date), zero narrative cues; rubric requires pure date comparison | CT4 uses an explicit narrative cue ("superseded by...") -- no date comparison needed |
| CT7 multi_hop_relational | "penalized by indirection/multi-hop reasoning" | Document names only a *team*; rubric provides two chained lookup tables (team→division, division→program) that must both be traversed | CT3 is a single direct lookup (project codename→folder) plus one override condition |
| CT8 long_context_distractor | "degrades with large irrelevant state content" | Same descriptive logic as CT1, but documents padded to ~500-700 words with plausible, irrelevant boilerplate (department history, disclaimers, unrelated appendices) surrounding the load-bearing sentences, deliberately not front-loaded | CT1 documents are ~120-220 words, no padding |

Design decisions confirmed with the user via explicit questions before
building: all 4 types built (not a subset); full scale (50 test + 10
validation per type, matching CT1-4); full A/B/C/SHUFFLE condition sweep
(cheap for Jev, keeps methodological consistency); **Haiku tested at full
scope** (matching Jev's 3-repeat × 4-condition scope), not skipped --
explicitly chosen over a Jev-only or reduced-scope Haiku comparison so the
new clause types could also speak to whether Jev's hard-mode weaknesses
(if any) still leave it ahead of the adoption-decision reference model.

Implementation follows the exact CT1-4 pattern: `rubrics/clause_specs.py`
gained `ClauseSpec` entries for CT5-8 (including `build_multihop_fixtures()`
for CT7's team→division→program tables, seeded on `"ct7_fixtures"`: 9 bird-
name teams split 3-per-division across `DIV-A/B/C`, divisions permuted onto
`program_atlas/borealis/cascade` -- not the "obvious" alphabetical mapping);
`rubrics/ground_truth.py` gained pure functions per type (CT5 sums
`metadata.line_items`, CT6 compares `date.fromisoformat` on both date
fields and asserts they're never equal, CT7 does the two-hop dict lookup,
CT8 reuses the `doc_type` field with a disjoint value set from CT1's);
`corpus/generate_metadata.py` gained per-type generators, each with its own
`sub_rng` stream, all following CT2's established hard/easy stratification
pattern (CT5: ~30% of docs have a sum within $300 of the threshold; CT6:
~30% have a date gap under 30 days). Re-running `generate_metadata.py`
after adding these was verified byte-identical on every CT1-4 field for
all 240 existing rows (only the new, all-`None`, CT5-8 schema fields
differed) before proceeding -- confirming the new generators didn't
perturb any already-scored CT1-4 predictions.

### Budget

Approved via explicit question to the user, given a cost projection of
~$6.49 against $1.06 remaining at the time (full CT5-8 corpus generation +
full Haiku scope): Anthropic budget raised from $5.00 to **$12.00**.
Actual corpus generation cost **$1.7974** (very close to the ~$1.79
estimate) for 240 new documents. CT8's documents required a much larger
per-batch output budget than CT1-7 (~500-700 words vs ~120-220): the
prose generator's `_max_tokens_for_batch` was made dynamic
(`corpus/prose_prompts.py`'s `max_tokens_estimate` field per doc-spec,
`corpus/generate_prose.py`'s `_max_tokens_for_batch`) rather than a fixed
4096-token ceiling, and CT8 batch size was reduced from 8→4→2 documents
after two truncation failures (`ValueError: batch response missing
documents`) at larger batch sizes -- both failures were mid-document
truncations near the output-token ceiling, not formatting errors, resolved
by giving more token headroom per document and fewer documents per call.

The full Haiku run (which, run without a `--repeats` override, also
transparently backfilled CT1-4's missing 3rd repeat -- see the §11
addendum above) ran the Anthropic budget down to $11.96/$12.00 with 33 of
2,880 CT8 predictions still outstanding. Rather than leave an arbitrary
33-prediction gap in the final CT8 numbers, the user approved a final
small top-up to **$12.50** to finish cleanly. Final actual Anthropic spend:
corpus generation $2.8561 total (CT1-4 $1.0587 + CT5-8 $1.7974), Haiku arm
$9.1786 total (all 8 clause types, full 3-repeat scope), for a combined
**$12.03 / $12.50** budget, $0.47 unspent. Jev spend across all 8 clause
types: $0.1809 total (separate provider, never touched the Anthropic
budget).

### Results: Jev found a real weakness (CT5), and two clean surprises

Full 3-repeat × 4-condition run (2,880 predictions per arm, matching CT1-4
scope exactly):

| Clause type | jev A | jev B | jev C | jev SHUFFLE | haiku A | haiku B | haiku C | haiku SHUFFLE |
|---|---|---|---|---|---|---|---|---|
| CT5 computed_threshold | 0.906 | 0.922 | 0.894 | 0.906 | 0.828 | 0.822 | 0.811 | 0.811 |
| CT6 temporal_reasoning | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.994 | 0.961 | 1.000 |
| CT7 multi_hop_relational | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| CT8 long_context_distractor | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

**Overall (CT5-8 combined, 2,880 predictions each)**: Jev 97.67%
(2,813/2,880, 95% CI [0.971, 0.982]), Haiku 95.17% (2,741/2,880, 95% CI
[0.944, 0.959]). Jev's hardmode-combined ceiling drops from its perfect
CT1-4 score but stays clearly ahead of Haiku's, which also drops -- both
models found the *same* genuine weak point (arithmetic), Jev just finds it
less.

**Finding 1 -- CT5 (arithmetic) is a real, isolated weakness for both
models, confirming the jaggedness doc's prediction, with Jev failing
noticeably less than Haiku.** Jev's 67 CT5 errors (out of 720) are **100%
concentrated in the "hard" bucket** (sums within $300 of the $5,000
threshold, by design ~30% of CT5 docs) -- manually confirmed by cross-
referencing every erroring `doc_id` against its `seed_trace.hard` flag.
66 of 67 errors are docs whose true sum is *under* $5,000 mispredicted as
*over* -- a one-directional bias (overestimating sums), not symmetric
noise. Per-document error rates within the near-threshold band are stark:
docs $12-$228 from the threshold fail 7-12/12 times each; the two docs at
the edges of the "hard" band (distance $227.59 and +$46.56) fail only
1/12 times each -- errors cluster tightly in the middle of the near-
threshold zone, not uniformly across it. Haiku's CT5 error rate (131/720 =
18.2%) is roughly double Jev's (67/720 = 9.3%), and unlike Jev's, Haiku's
CT5 accuracy is flat across conditions (~81-83%) rather than concentrated
purely by numeric distance -- consistent with Haiku's arithmetic mistakes
being a more diffuse weakness rather than Jev's sharply threshold-
localized one.

**Finding 2 -- CT7 (multi-hop) and CT8 (long-context distractor) were
NOT differentiating: both models hit 100.00% on both, across every
condition.** This contradicts the a priori expectation (from the
jaggedness doc) that multi-hop indirection and long irrelevant context
would be hard for Jev specifically. Read charitably: at this scale (a
two-hop, 9-entry lookup table; ~500-700 word documents with padding), both
capabilities are already saturated for both models, and a harder version
of either design (a 3+ hop chain; documents padded to several thousand
words) would be needed to actually locate a breaking point. This is
recorded as a negative result, not suppressed: the hypothesis was
reasonable and testable, and it didn't pan out at this scale.

**Finding 3 -- CT6 (temporal reasoning) surfaces a second, distinct
flavor of content-prior contamination in Haiku, absent in Jev.** Jev:
100.00% across all 4 conditions. Haiku: 100.00% on A/SHUFFLE, 99.44% on B,
**96.11% on C** (8 errors out of 720). All 8 of Haiku's CT6 errors share
one mechanism, confirmed by inspecting Condition C's actual rubric text
for this clause type: Condition C's derangement (only 2 possible
permutations for 2 folders, so it's the full swap) makes the canonical
"current_version" folder *display* as `prior_version` and vice versa --
e.g. the literal rubric sentence reads "...file it under `prior_version`"
for the case where the document IS the newest version. In every one of
Haiku's 8 errors, it correctly identifies the temporal relationship
(the date comparison itself isn't the failure) but then outputs the
display name that is *semantically* consistent with plain-English
folder-name meaning ("prior_version" for an older-sounding case) rather
than the literal, adversarially-permuted mapping actually stated in the
rubric -- all at confidence 0.95-1.00 (confidently wrong). This is
mechanistically distinct from CT3's prefix-matching confusion (§11) but is
the same underlying failure mode the whole benchmark is designed to
detect: letting label semantics override a stated rule. Across all of
CT1-8, Jev shows zero errors in any Condition C or SHUFFLE cell except the
CT5 arithmetic cluster -- and that cluster's error rate is essentially flat
across A/B/C/SHUFFLE (0.894-0.922, no directional pull toward any
particular condition), confirming it's a numeric-distance effect, not a
label-semantics effect.

**Finding 4 -- Jev's confidence is decision-usefully calibrated on its one
real weakness; Haiku's is not.** This is the sharpest, most decision-
relevant number in this section, directly answering test-plan.md §6's
framing of calibration as "the single most decision-relevant number... for
a firm that plans to keep a fallback path." Restricted to CT5 (where
nearly all errors live):

| Arm | Confidence at CT5 errors | Confidence at CT5 correct | Gap |
|---|---|---|---|
| Jev | 0.433 (n=67) | 0.911 (n=653) | **0.478** |
| Haiku | 0.986 (n=131) | 0.987 (n=589) | **0.001** |

Jev's confidence on CT5 errors averages less than half its confidence on
CT5 correct predictions -- a large, usable signal: a review-queue rule of
"flag anything under ~0.6 confidence" would catch the overwhelming
majority of Jev's arithmetic mistakes. Haiku's confidence is statistically
indistinguishable between its errors and its correct predictions on the
identical task -- it fails *confidently*, giving a downstream system
nothing to act on. Full-corpus (all 8 clause types) calibration confirms
the same pattern in aggregate: Jev's raw ECE is 0.033 (temperature-fit on
the validation split: T=0.2, fitted ECE 0.011), Haiku's raw ECE is lower
in the aggregate (0.0098, since Haiku is *mostly* very confident and
*mostly* correct, which flatters overall ECE) but this is exactly the
metric test-plan.md's calibration section warns is insufficient on its
own -- confidence-at-errors is what actually matters for a fallback-queue
design, and there Jev's advantage is unambiguous.

**Run-to-run disagreement (CT5-8, 3 repeats each)**: Jev 5/1,920 = 0.26%,
Haiku 28/1,920 = 1.46% -- consistent with the CT1-4 pattern (§11 addendum),
Jev is meaningfully more repeat-to-repeat stable.

**Baselines (nli-bart, emb-bge) on CT5-8**: both collapse to
near-chance across the board except CT8 Condition A (nli-bart 0.80,
emb-bge 0.75 -- label-text similarity still works when the folder name
genuinely matches the document genre and there's no misleading swap) and
CT8 Condition C, where both drop *below* their own SHUFFLE numbers
(nli-bart 0.10 vs 0.30, emb-bge 0.083 vs 0.417) -- the misleading label
swap makes a text-similarity matcher *confidently wrong* in a consistent
direction, replicating the CT1 pattern from Part 1 in the padded-document
setting. CT5/CT6/CT7 sit at or near chance (0.27-0.55) in every condition
for both baselines, as expected: neither arm reads rubric text, so
questions requiring arithmetic, date comparison, or multi-hop lookup are
simply unanswerable to them regardless of folder naming.

### Takeaway

CT1-4 established that Jev genuinely conditions on the rubric rather than
matching content priors. CT5-8 answers the follow-up question the user
raised: Jev does have a real, specific limit -- arithmetic near a stated
threshold -- and it's exactly the limit the vendor's own jaggedness
documentation predicted. But (a) Jev fails *less* on that limit than the
reference-ceiling LLM (9.3% vs 18.2% error rate), (b) Jev's confidence
degrades sharply and usefully on exactly the cases it gets wrong, where
Haiku's does not, and (c) two other a priori plausible weaknesses
(multi-hop indirection, long-context distraction) did not materialize as
weaknesses at all at this scale for either model. Net effect on the Part 2
adoption decision (test-plan.md §6): unchanged from §11's conclusion --
Jev remains ahead of Haiku on accuracy, now demonstrated on a corpus that
was deliberately designed to break it, not just one it happened to ace.
