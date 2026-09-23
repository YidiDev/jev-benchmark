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
cost/latency) built and used to produce the numbers below. CT9 chained
decision-tree execution (§13) complete for jev and haiku, full 3-repeat
scope across all k values and both folder-labeling schemes. OpenJev (§14)
complete for both CT1-8 and CT9, full scope, matching Jev's own -- free
Codiv tier, $0 cost. CT10 AP World History exam grading (§15) complete
for all three arms (jev, haiku, openjev), full scope: 100 students x 30
questions x 2 grading modes x 2 key-conditions. Final Anthropic spend:
$41.26 / $50.00 budget.**

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
decisive result under test-plan.md §6's comparison framework ("Jev >= Haiku
on accuracy" reads as a decisive result in Jev's favor); a third model
doesn't change that conclusion, and
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
(if any) still leave it ahead of the Part 2 comparison's reference model.

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
comparison (test-plan.md §6): unchanged from §11's conclusion --
Jev remains ahead of Haiku on accuracy, now demonstrated on a corpus that
was deliberately designed to break it, not just one it happened to ace.

## 13. CT9: chained decision-tree execution

### Motivation and design history

CT1-8 all share one structural shape: one document, one Choice call, one
folder. This section asks a different question -- can either model
correctly **execute a long chain of conditional logic**, where getting a
late step right depends on having gotten every earlier step right too?
This is a distinct capability from rubric-following (CT1-8): a model could
condition perfectly on a single-hop rubric and still fail at chaining ten
sequential decisions, since each additional hop is a fresh opportunity for
drift, and there's no free "resync to ground truth" between hops in any
realistic deployment.

The design went through several iterations, documented here because the
rejected ideas are informative about what this section deliberately does
NOT test:

1. **First idea (rejected):** build the decision tree over word-position/
   orthographic predicates of the *existing* CT1-8 document text (e.g. "is
   the 3rd word a noun starting with a vowel"), reusing the corpus for
   zero generation cost. **User caught the flaw before any of it was
   built**: "I think it'll do pretty badly at that. even LLMs are known
   for being bad at any of that because they think in tokens." Correct --
   character/word-position counting is a tokenization artifact that would
   fail any LLM roughly equally regardless of rubric-following or
   reasoning ability, confounding the very thing this benchmark exists to
   isolate. Discarded entirely.
2. **Final design:** a 30-question natural-language compliance/eligibility
   screening questionnaire (job-application-style), identical questions
   across all forms, different natural colloquial answers per form. Tests
   two capabilities together: normalizing free text into a structured
   judgment, and chaining those judgments through a deep decision tree.
   Corpus generated fresh (structured answers via seeded RNG first, then
   Sonnet paraphrase -- same two-stage pipeline as CT1-8) so the folder
   distribution could be engineered balanced rather than discovered.

### The tree

`qtree/tree.py`: a 10-layer DAG, `LAYER_WIDTHS = [1,2,3,3,4,4,3,3,2,3]` (28
decision nodes), terminating in 5 folders
(`F_auto_approve`/`F_manual_review_minor`/`F_manual_review_major`/
`F_auto_reject`/`F_escalate_compliance`). Every root-to-folder path is
exactly 10 edges. 25 of the 28 nodes are standard binary questions drawn
from a 27-question bank (`qtree/questions.py`); 3 nodes (one each in
layers 4, 7, 9) are "special" 4-way nodes combining an
**instruction-following check** (was the answer within the stated "3
sentences or less" limit -- verified mechanically by counting sentences in
the actually-generated text, same self-correcting principle as CT5's
line-item sums) with a **content-correctness check** (does the answer
correctly state a real policy fact, e.g. "client records retained for 7
years" -- trusted from generation intent, like CT3/CT4's other prose
facts), producing a genuine 4-way branch
(`compliant_correct`/`compliant_wrong`/`noncompliant_correct`/
`noncompliant_wrong`) instead of a binary one. Construction
(`build_tree()`) is a coverage pass (guarantee every next-layer node has
>=1 incoming edge) followed by a random convergence pass, both seeded via
`sub_rng`, fully deterministic. Caught and fixed two real bugs during
construction: the last layer needed to be width-3 rather than width-2 (2
binary nodes' 4 total edges can't cover 5 folders), and an early
reachability-guarantee implementation used stale incoming-edge counts
across sequential fixes, leaving `F_manual_review_major` completely
unreachable in one build -- fixed by recomputing incoming counts fresh
before each fix and only reassigning edges with redundant (>1) incoming
coverage, so a fix can never silently orphan a different target.
Simulated-balance check (20,000 draws, independent RNG stream): 13.8%-27.7%
per folder, well-balanced. Corpus: 60 forms (`qtree/generate_metadata.py`,
10 test + 2 validation per folder x 5 folders), prose via
`qtree/generate_prose.py` (Sonnet 5, same non-Haiku rationale as CT1-8).
**Cost: $1.8114** (55 calls). One real generation bug found and fixed:
batching multiple 30-question forms per Sonnet call reliably failed to
follow the exact output format at this Q&A density (not a token-budget
issue -- confirmed via a batch that stopped at `end_turn` with budget to
spare but still only wrote one of two forms); fixed by switching to
`batch_size=1` plus a lenient fallback parser.

### Execution mode: chunk size k

The central design question, refined over several rounds with the user:
how much of the 10-layer chain does one model call get to execute before
handing off? Parameterized as **chunk size k** in `{1, 2, 5, 10}` --
`qtree/subtree.py`/`qtree/runner.py` walk the tree in `10/k` chunks.
**Chunk 1 always starts at the true root.** Every subsequent chunk starts
from **wherever the model's own previous chunk answer actually landed** --
explicitly *not* rescued back to the ground-truth-correct position between
chunks, per the user's clarification ("I do want [k=]2 and [k=]5 as well")
after an initial proposal for isolated, ground-truth-anchored per-step
measurement was set aside in favor of genuine compounding. k=10 is a
single call tracing the whole tree at once (no handoffs). k=1 is maximum
external orchestration (10 calls, 10 real handoffs). Each chunk call gets
the full 30-Q&A form transcript as state plus a textual description of
every decision node reachable within the next k steps from the current
position (question text + where each answer leads, built by
`qtree/subtree.describe_subtree`), and must choose among all node/folder
ids reachable in exactly k steps. A free diagnostic falls out of this for
every chunk: whether that specific chunk's answer was **locally correct**
given wherever the model actually claimed to start (not necessarily the
globally-true node) -- this decomposes end-to-end failure into "bad at
individual steps" vs. "fine locally, drifts and compounds."

**Semantic vs. opaque folder labels, k=10 only.** Unlike CT1-4's A/B/C
conditions (which apply this axis everywhere), this check is scoped to
k=10 alone: intermediate chunks in k=1/2/5 land on internal node ids
(`n7_2` etc.), which carry no semantic content to begin with, so the
axis is inapplicable there. At k=10 specifically, the 5 outcome folders
*do* carry real semantic correlation with document content (a form full of
red flags plausibly "sounds like" `F_auto_reject`), creating genuine
shortcut risk that CT1-4's simple classification never had -- this check
exists to rule out "the model guessed the vibe" as an explanation for the
k=10 headline number.

### Pipeline and cost

`qtree/arms.py`: `JevChunkArm`/`HaikuChunkArm`, structurally identical to
`arms/jev.py`/`arms/haiku.py` (state = form transcript, instructions =
subtree description, options = k-step destinations) but returning a
`ChunkPrediction` rather than a document-level `Prediction`.
`qtree/predictions.py`: `ChunkRecord` storage (one JSONL row per chunk,
not per trace, since a trace is a *sequence*) at
`results/predictions/qtree_{arm}.jsonl`, grouped into traces by
`(form_id, k, repeat, labeling)`; resumable by reconstructing each trace's
current position from whatever chunks are already on disk.
`qtree/runner.py`: `python -m qtree.runner --arm {jev,haiku}`.

Small real-sample validation (1 form, all 4 k values, both labelings at
k=10) confirmed the pipeline end-to-end before the full run, including
one qualitatively rich example: Haiku's k=1 trace on `qt_te_001` made
exactly one high-confidence local error at chunk 6 (n7_0→n8_0 instead of
the correct n8_1, confidence 0.85), after which every subsequent chunk was
locally correct **relative to its new, wrong position** -- 9/10 individual
decisions technically "correct-given-where-it-was," yet the trace still
landed on the wrong folder. Exactly the "fine locally, drifts and
compounds" failure mode this design exists to detect.

Full run: 60 forms x {k=1,2,5,10} x 3 repeats x (2 labelings at k=10 only)
= 900 traces = 3,420 chunk calls per arm, matching the ~3,420-call estimate
presented to the user when requesting the budget increase to $30.00.
**Cost: Jev $0.3192 (3,420 calls, negligible, separate provider), Haiku
$10.2672 (3,420 calls).** Combined with CT1-8's spend, final Anthropic
total: **$24.11 / $30.00 budget, $5.89 remaining.**

### Results

**End-to-end accuracy by k (bootstrap 95% CI):**

| k | jev (semantic) | haiku (semantic) |
|---|---|---|
| 1 | 0.750 [0.689, 0.817] | 0.578 [0.511, 0.650] |
| 2 | 0.711 [0.644, 0.778] | 0.533 [0.461, 0.606] |
| 5 | 0.311 [0.239, 0.378] | 0.317 [0.250, 0.389] |
| 10 | 0.294 [0.228, 0.361] | 0.317 [0.250, 0.383] |
| 10 (opaque) | 0.339 [0.272, 0.411] | 0.317 [0.250, 0.389] |

**Finding 1 -- accuracy degrades as k *increases*, the opposite of the
naive compounding-error prediction.** Going in, the expectation was that
*more* handoffs (lower k) would hurt accuracy, since every handoff is a
fresh chance to drift. The data says the reverse: both models do
*dramatically* better with frequent small handoffs (k=1: Jev 75.0%, Haiku
57.8%) than with a single unassisted full-chain trace (k=10: Jev 29.4%,
Haiku 31.7%). Real compounding does happen at low k (see the local-vs-
end-to-end breakdown below), but it costs far less accuracy than the
alternative: holding all 28 nodes' branching logic in context and
correctly chaining through 10 of them in one shot is a much harder
combined-reasoning task than making 10 separate, freshly-scoped 1-step
judgments. Practically: **external orchestration that checkpoints
progress between small steps is worth more to both models than any
efficiency gained by asking for the whole chain at once** -- a genuinely
actionable finding for anyone building a similar decision-chain system on
either model.

**Finding 2 -- Jev's edge is concentrated at small step sizes, and
vanishes at k=5/10.** Jev beats Haiku by double digits at k=1 (75.0% vs
57.8%, +17.2pp) and k=2 (71.1% vs 53.3%, +17.8pp), but the two are
statistically indistinguishable at k=5 (31.1% vs 31.7%) and k=10 (29.4%
vs 31.7%, Haiku marginally *ahead*, within CI overlap). Jev's advantage
here is specifically about **execution discipline at the small-step
scale** -- correctly answering one clearly-scoped question and correctly
carrying its own position forward -- not about raw multi-hop reasoning
capacity within a single call, where both models degrade to roughly the
same level.

**Finding 3 -- the semantic-vs-opaque check at k=10 finds no shortcut
effect for either model.** Jev: 29.4% semantic vs 33.9% opaque (opaque
slightly *higher* -- the opposite direction a "vibes-based shortcut" story
would predict). Haiku: 31.7% vs 31.7%, identical. If either model were
substituting folder-name semantics for genuine tree traversal at k=10,
opaque labels (which strip that signal) should have made performance
*worse*, not flat-to-better. This cleanly rules out the shortcut-guessing
concern this check was designed to catch: both models are genuinely
attempting (and largely failing) real 10-hop traversal in a single call,
not pattern-matching on folder names.

**Finding 4 -- local (per-chunk) accuracy vs. end-to-end accuracy
decomposes "bad at steps" from "drifts and compounds."**

| k | jev local acc | haiku local acc | jev all-chunks-correct rate | jev end-to-end | haiku all-chunks-correct rate | haiku end-to-end |
|---|---|---|---|---|---|---|
| 1 | 0.960 | 0.911 | 0.656 | 0.750 | 0.356 | 0.578 |
| 2 | 0.921 | 0.848 | 0.622 | 0.711 | 0.378 | 0.533 |
| 5 | 0.483 | 0.456 | 0.200 | 0.311 | 0.206 | 0.317 |
| 10 | 0.317 | 0.317 | (=end-to-end, single chunk) | | | |

Jev's per-chunk local accuracy at k=1 (96.0%) roughly predicts its
all-chunks-correct rate under independence (0.96^10 ≈ 66.5%, observed
65.6% -- close): most of the 10 steps really are close to independent
per-step judgments. But **end-to-end accuracy consistently exceeds the
all-chunks-correct rate** for both models at every k<10 (e.g. Jev k=1:
75.0% end-to-end vs. 65.6% zero-local-errors) -- meaning a meaningful
fraction of traces reach the *correct* final folder despite at least one
locally-wrong step along the way. This is the tree's real convergence
(multiple paths lead to the same folder by design) rescuing some
off-path wanderings, not an artifact -- and it means end-to-end accuracy
alone somewhat *understates* how much a single misstep actually costs,
since some missteps are free.

**Finding 5 -- Jev's confidence discriminates local correctness sharply;
Haiku's barely does, replicating CT5's calibration finding in a completely
different task.** Mean confidence at locally-incorrect chunks vs.
locally-correct chunks: Jev 0.400 (n=575) vs. 0.885 (n=2,845) -- a 0.485
gap. Haiku 0.928 (n=740) vs. 0.976 (n=2,680) -- a 0.048 gap, roughly 10x
smaller. This is the same asymmetry found in CT5 (methodology.md §12,
Finding 4), now confirmed on a structurally unrelated task: Jev's
confidence is a genuinely actionable signal for flagging likely-wrong
steps mid-chain; Haiku's confidence stays high almost regardless of
whether the step was actually right.

**Finding 6 -- a genuine reversal: Jev shows more run-to-run disagreement
than Haiku at k=10.** Directly comparable to CT1-8's disagreement metric
(single call, 3 repeats): Jev 5/60 = 8.33% of forms gave a different final
answer across repeats at k=10; Haiku 0/60 = 0%. This runs counter to every
CT1-8 finding, where Jev was consistently *more* stable (e.g. CT1-8
overall disagreement Jev 0.26-0% vs. Haiku 0.73-1.46%, methodology.md
§11-12) -- reported here without smoothing it over, since a benchmark that
only ever finds Jev-favorable results isn't trustworthy. Plausible
reading: k=10's single-shot full-tree trace is a genuinely hard task for
Jev specifically (its accuracy there, 29.4%, is its lowest anywhere in
this entire benchmark), and instability under difficulty is a reasonable
expectation that just never surfaced elsewhere because CT1-8 never pushed
Jev hard enough to see it.

### Takeaway

CT9 is a capability CT1-8 never tested: chaining many sequential
decisions where each depends on getting the previous ones right. The
headline result inverts the a priori hypothesis -- external orchestration
(more, smaller handoffs) dramatically *helps* both models rather than
hurting them via compounding, and Jev's real advantage over Haiku is
concentrated specifically in that small-step, frequently-checkpointed
regime (+17-18pp at k=1/2), not in raw single-shot multi-hop capacity
(statistically tied at k=5/10). The semantic/opaque check rules out
shortcut-guessing as an explanation for either model's k=10 number. The
calibration asymmetry from CT5 replicates cleanly on this unrelated task.
And the one place this section found Jev *less* stable than Haiku --
run-to-run disagreement at k=10 -- is reported as found, not filtered,
because it's exactly the kind of genuine limit this whole hard-mode
effort exists to surface.

## 14. OpenJev: the fallback-viability arm (test-plan.md Part 3)

`CODIV_API_KEY` became available (user added it to `.env` mid-benchmark);
`CODIV_BASE_URL` defaulted to `https://api.codiv.ai` per `.env.example`.
Live connectivity confirmed both primitives work identically to Jev's own
API: a `Choice` call classified a test invoice correctly (model reports
itself as `openjev-0.1` under the `openjev-latest` alias), and a `Score`
call worked once `criteria` was passed as an ordered `Sequence` rather
than a dict (a real API signature difference from `Choice`'s
`dict[str, str]` criteria -- caught by a live test before assuming the
two primitives share an interface).

`arms/openjev.py` (`OpenJevArm`) and `qtree/arms.py`'s `OpenJevChunkArm`
are structurally identical to their Jev counterparts -- same `Choice`
decomposition, same state/instructions/criteria shape -- differing only in
`base_url`/`api_key`, which is the entire point of testing this arm: it's
supposed to be a drop-in replacement. Both were run at full scope,
matching Jev's own: CT1-8 (5,760 calls: 480 docs × 4 conditions × 3
repeats) and CT9 (3,420 chunks: 900 traces across all k values, matching
§13's exact scope). Free Codiv tier -- **$0 cost, never touches the
Anthropic budget** -- but noticeably slower per call than Jev's paid API
(each full CT1-8/CT9 run took multiple 5-minute tool-timeout cycles to
complete via resumption, vs. single or double cycles for Jev), consistent
with running on a smaller, shared, free-tier-hosted inference backend
rather than TypeSafe's own production infrastructure.

### CT1-8 results: strong overall, with one sharp, mechanistically-understood failure

**Overall accuracy: 96.28%** (5,546/5,760, 95% CI [0.958, 0.968]) --
between Haiku's 97.74%(CT1-4)/95.17%(CT5-8) and Jev's 100%/97.67%, but
with a qualitatively different error profile: one clause-type/condition
cell collapses hard while everything else stays strong.

| Clause type | A | B | C | SHUFFLE |
|---|---|---|---|---|
| CT1 descriptive | 0.989 | 1.000 | 1.000 | 0.944 |
| CT2 conjunctive_threshold | 1.000 | 1.000 | 1.000 | 1.000 |
| CT3 relational | 0.972 | 0.956 | 0.950 | 0.983 |
| CT4 negative_exclusionary | 1.000 | 1.000 | 1.000 | 1.000 |
| CT5 computed_threshold | 0.917 | 0.889 | 0.917 | 0.917 |
| CT6 temporal_reasoning | 1.000 | 1.000 | 1.000 | 0.983 |
| CT7 multi_hop_relational | 1.000 | 1.000 | **0.400** | 1.000 |
| CT8 long_context_distractor | 1.000 | 0.994 | 1.000 | 1.000 |

**Finding 1 -- CT5 arithmetic weakness replicates for a third model,
same signature.** 65 errors, **100% within the near-threshold "hard"
bucket** -- exactly the pattern found in both Jev (§12) and Haiku (§12),
strong convergent evidence this is a genuine, threshold-proximity-driven
arithmetic limitation shared across model families, not an artifact of
any one implementation.

**Finding 2 -- a sharp, mechanistically-diagnosed collapse: CT7 Condition
C, 40.0% (108/180 errors), while CT7's shuffle control stays at 100%.**
This is the standout finding for OpenJev specifically. Traced to source:
grouping errors by which physical division a document's team belongs to
reveals a clean, deterministic pattern -- **every DIV-A document (180/180
across 3 teams) is misrouted to the program that DIV-B's teams correctly
route to; DIV-B documents are never wrong (0/180); DIV-C documents are
mostly wrong (108/180), split between the program DIV-A's teams correctly
route to and (rarely) DIV-B's.** In other words: OpenJev's two-hop lookup
(team -> division -> program) breaks specifically when Condition C's
derangement relabels all three programs with *other real, equally
plausible* program names (a genuine 3-cycle: canonical `program_atlas` ->
displayed `program_borealis` -> displayed `program_cascade` -> displayed
`program_atlas`) -- it silently lands on a different division's
genuinely-valid label rather than the specific one actually stated for
its own division. Critically, **this is not simply "adversarial relabeling
defeats it"**: the SHUFFLE control, which relabels the exact same
canonical programs with fully opaque random-character ids instead of
other meaningful program names, scores a perfect 1.000 on the identical
underlying tree and lookup logic. The failure is specific to *label
collision risk* -- when a wrong answer is also a real, plausible-looking
label for the same question, OpenJev has a meaningfully higher chance of
landing on it than when a wrong answer is just a random string with no
semantic pull. Jev and Haiku both score 1.000 on this exact cell (§12),
making this the single clearest quality gap found between OpenJev and the
two other arms anywhere in this benchmark.

**Finding 3 -- shuffle-control tracking confirms OpenJev does genuinely
condition on the rubric, same as Jev.** B-vs-SHUFFLE delta is small in
every clause type (-0.028 to +0.056, no clear direction), meaning under
opaque-id relabeling specifically (as opposed to Condition C's
meaningful-but-permuted relabeling), OpenJev tracks the permuted mapping
just as well as the semantically-obvious one -- ruling out "OpenJev is
just guessing based on content priors" as the explanation for Finding 2.
The CT7 collapse is a real execution/label-collision failure under one
specific adversarial condition, not evidence of a broader failure to
follow the stated rubric.

**Finding 4 -- calibration.** Confidence at errors (0.396, n=214) vs. at
correct (0.901, n=5,546) -- a 0.505 gap, comparable to Jev's own CT1-8
calibration discrimination and far better than Haiku's near-zero gap
(§12). Raw ECE 0.0795 (worse than both Jev's 0.0331 and Haiku's 0.0098 in
aggregate), fitted ECE 0.0514 at T=0.5 -- OpenJev's raw confidence values
are less well-calibrated in the aggregate sense than either other arm, but
still meaningfully discriminate errors from correct predictions, which is
the more decision-relevant property per §12 Finding 4's framing.

**Disagreement**: 16/1,920 = 0.83% -- between Jev's 0.26% and Haiku's
1.46% on the equivalent CT5-8 comparison.

### CT9 results: same qualitative pattern, weaker in absolute terms

| k | jev | haiku | openjev |
|---|---|---|---|
| 1 | 0.750 | 0.578 | 0.428 |
| 2 | 0.711 | 0.533 | 0.256 |
| 5 | 0.311 | 0.317 | 0.194 |
| 10 (semantic) | 0.294 | 0.317 | 0.156 |
| 10 (opaque) | 0.339 | 0.317 | 0.206 |

OpenJev replicates §13's headline qualitative finding -- accuracy is
highest at k=1 and degrades monotonically as k increases -- but sits
below both other arms at every k, and degrades faster (k=1 to k=5 drops
42.8 points for OpenJev vs. 43.9 for Jev and 26.1 for Haiku -- comparable
raw drop to Jev's but from a much lower starting point, and steeper than
Haiku's). Local (per-chunk) accuracy: 85.5% (k=1) down to 18.1% (k=10),
confirming this is a genuine, broad-based execution weakness at longer
per-call chains, not confined to one clause type the way the CT1-8 CT7
finding was. Confidence discrimination is intermediate between Jev's and
Haiku's: 0.484 (local errors) vs. 0.702 (local correct), a 0.218 gap --
real signal, smaller than Jev's 0.485 but far better than Haiku's 0.048.
Disagreement at k=10: 8/60 = 13.3%, the highest of the three arms (Jev
8.3%, Haiku 0%) -- OpenJev is the least run-to-run stable arm on this
benchmark's hardest single task.

### Fallback-viability verdict (test-plan.md Part 3's question)

OpenJev is a **genuinely viable fallback for CT1-8-style rubric
classification** (96.28% overall, one narrow but real gap at CT7/misleading
that a routing rule could specifically guard against -- e.g. avoid
opaque/misleading conditions for multi-hop clause types, or add a
verification pass there specifically) at **zero marginal cost**. It is
**not currently a viable substitute for CT9-style chained execution**:
its accuracy is meaningfully lower than both Jev and Haiku at every chunk
size, its per-chunk local accuracy degrades faster, and it is the least
stable of the three arms on repeated runs of the hardest single-shot
task. A firm treating Jev as primary with OpenJev as a cost-free fallback
should scope that fallback to the simpler, single-hop classification
tasks this benchmark's CT1-8 represents, not to long decision chains.

## 15. CT10: AP World History exam grading

### Motivation and design

CT1-9 both test *classification*-shaped tasks: given a document or a
chained decision, pick one folder. CT10 tests a different capability
combination the user specifically asked for: **applying a partial-credit
rubric to open-ended paragraph answers** -- a genuine scoring/generation
judgment, not a forced choice among discrete options -- plus a second,
orthogonal axis: **does the grading model need the answer key, or does it
already know the material?** These are two different questions an
automated-grading deployment would actually need answered, and CT1-9's
single-Choice-per-document decomposition can't speak to either.

Design decisions, all confirmed with the user via explicit questions
before building:

- **30 questions, realistic non-uniform rubric summing to exactly 100
  points** (5 questions worth 2, 12 worth 3, 11 worth 4, 2 worth 5) --
  matched to how many genuinely distinct, checkable elements each
  specific AP World History short-answer prompt naturally has, not an
  arbitrary RNG assignment independent of content (unlike CT1-9's
  RNG-driven choices, a checklist rubric's length is inherently tied to
  what the question is actually asking).
- **Checklist-style rubrics with a separate answer key**: each question's
  `criteria` (`examgrade/questions.py`) describe structurally what kind
  of content earns a point (e.g. "identifies a specific triggering
  event") without ever stating the actual correct answer; the actual
  correct content lives in a separate `reference_facts` list, appended to
  the rubric text only when grading `with_key=True`
  (`examgrade/rubric_text.py`). This is the same discipline as CT5's
  "no stated total" and CT6's "no superseded language" -- verified
  directly: `test_without_key_excludes_reference_facts` and
  `test_full_exam_rubric_without_key_never_leaks_any_fact` assert no
  `reference_fact` string ever appears in the without-key rubric text an
  arm actually receives.
- **100 students, one latent ability parameter per student** (Beta(2,2),
  seeded per student), not independent per-question randomness -- the
  user's explicit choice, since real students are consistent across an
  exam, not random question-to-question. Per-question true score =
  `ability + Gaussian(0, 0.15) noise`, clipped to [0,1], scaled to that
  question's point value and rounded (`examgrade/generate_metadata.py`).
  Verified: correlation(ability, total_true_score) = 0.992 across the
  100 generated students (strong but not perfect, confirming individual-
  question noise survives averaging without swamping the ability signal);
  total scores ranged 4-94 out of 100, a realistic spread.
- **Which specific criteria a partial-credit answer satisfies is itself
  seeded-RNG-chosen** (`examgrade/prose_prompts.select_satisfied_criteria`),
  not always "the first N" -- a student who earns 2 of 5 points might
  correctly cover any 2 of the 5 elements, matching how a real student's
  partial recall doesn't cluster at the start of a rubric.
- **Two grading modes**: chained (one call per question, isolated
  context, matching CT9's k=1) and whole-exam (one call grades all 30
  questions, matching CT9's k=10) -- the user's explicit choice to keep
  whole-exam mode itemized (per-question scores summed to a total) rather
  than a single holistic total-score guess, so the two modes are directly
  comparable at the same granularity and the only real variable is
  isolated-vs-shared context, not also a change in what's being measured.
- **Two key-conditions x two modes, no third axis for repeats**:
  `repeats=1` throughout (user's explicit choice, given the already-large
  combinatorial scope), and **no held-out validation split** (also
  explicit -- calibration temperature-fitting wasn't the goal here).
- **Three arms: Jev, Haiku, OpenJev** -- all three, decided after
  `CODIV_API_KEY` became available mid-planning (§14); the original plan
  had OpenJev optional/deferred, but the user asked for it included from
  the start once the key existed.

### Corpus generation

`examgrade/generate_prose.py`: one Sonnet 5 call per student generates
all 30 of their answers at once (batch_size=1 per student -- learned
directly from CT9's lesson that batching multiple 30-item forms per call
breaks output-format-following at this Q&A density; exam answers here are
even longer, full paragraphs rather than 1-2 sentences, so batching
students together would only have been riskier). Manual verification on
the first generated student (`student_001`) cross-checked against ground
truth: 4 spot-checked questions (q01=1/3, q02=1/4, q08=2/3, q13=2/5) all
had generated answers covering *exactly* the RNG-selected subset of
criteria, confirming the generation pipeline faithfully encodes intended
partial credit rather than just approximating it.

**Cost: $6.9246** (105 calls -- 100 students plus 5 retries from
transient parse/format misses, discussed below). Real per-student cost
ranged roughly $0.044-$0.157, averaging ~$0.066/student; higher than the
CT9-derived ballpark estimate, consistent with fuller paragraph answers
generating more output tokens than CT9's short colloquial responses.

**Operational issues encountered and resolved** (documented so they
aren't re-debugged): (1) 5 of 100 students hit the same class of parsing
failure CT9 saw -- a response missing one `===ANSWER qXX===...===END===`
block despite `stop_reason=end_turn` (not a token-budget truncation) --
resolved by simply retrying (Sonnet's non-deterministic sampling meant
the retry always succeeded; a live debug re-run of one failing case
produced a perfectly well-formed response on the next attempt, confirming
this is sampling variance in output-format adherence, not a deterministic
per-student content issue); (2) one transient Anthropic `500 Internal
Server Error`, resolved the same way (resume/retry). Both failure classes
bill the API call before the parse/network failure is caught, so a small
amount of double-billing occurred (~5-6 extra calls' worth, reflected in
the 105-vs-100 call count) -- immaterial at this cost scale.

### Grading arms

`examgrade/arms.py`. Jev and OpenJev share an implementation
(`_TypeSafeGradingArm`) differing only in client configuration, per this
benchmark's established pattern. **First use of Jev's `Score` primitive**
anywhere in this benchmark (CT1-9 only ever used `Choice`): each question
is graded via a `Score` question with `points + 1` ordered levels ("0 of
N criteria satisfied" through "N of N criteria satisfied"),
`instructions` carrying the rubric text (with or without the key per
condition). One live API quirk caught before building further: `Score`'s
`criteria` parameter is a `Sequence[str]` (ordered list), not a
`dict[str, str]` like `Choice`'s -- confirmed via a live test call that
raised a Pydantic validation error on the first (dict-based) attempt, and
via `Score.__init__`'s own signature.

**Whole-exam mode exploits a genuine architectural difference between
Jev/OpenJev and Haiku.** Jev/OpenJev's `system_one` call natively accepts
multiple questions evaluated together (documented: "Three question types
in one call, evaluated in parallel") -- so whole-exam mode for these two
arms is one call with 30 separate `Score` questions, state = the
student's full exam transcript, each question still carrying its own
independent rubric instructions. Haiku has no equivalent multi-question
primitive; its whole-exam mode instead uses **one forced tool call with a
dynamically-built JSON schema containing one integer property per
question** (`{"scores": {"q01": int, ..., "q30": int}}`, each bounded to
that question's own point range) -- a single shared judgment producing 30
numbers at once, structurally different from Jev's "many small parallel
judgments bundled into one call." This architectural difference turns
out to matter a great deal (Finding 2, below).

### Scope and cost

100 students x 30 questions x 2 key-conditions x 2 modes = 6,200
grading actions per arm (chained: 100x30x2=6,000; whole-exam: 100x2=200),
x 3 arms = 18,600 total. Small real-sample validation (1 student, both
modes, both key-conditions, all three arms) confirmed the pipeline
end-to-end and gave real per-call cost data before the full run, per this
project's established practice.

**Final cost**: Jev $0.2519 (6,203 calls -- negligible, separate
provider), **Haiku $10.2225** (6,208 calls), **OpenJev $0.00** (6,202
calls, free tier). Every arm produced 12,000 stored grade rows (100
students x 30 questions x 2 modes x 2 key-conditions). Combined with all
prior phases, cumulative Anthropic spend after CT10: **$41.26 / $50.00
budget, $8.74 remaining.**

### Results

**Per-question grading accuracy (exact-match rate against the true
score, 100 students x 30 questions = 3,000 gradings per cell):**

| Arm | Mode | Without key | With key |
|---|---|---|---|
| Jev | chained | 0.802 | 0.872 |
| Jev | whole_exam | 0.827 | 0.876 |
| Haiku | chained | 0.832 | 0.862 |
| Haiku | whole_exam | 0.683 | 0.708 |
| OpenJev | chained | 0.731 | 0.790 |
| OpenJev | whole_exam | 0.577 | 0.570 |

**Finding 1 -- all three arms grade meaningfully better with the answer
key than without it, but by very different margins**, directly answering
the user's "test how well these models know the information" question:

| Arm | Chained delta | Whole-exam delta |
|---|---|---|
| Jev | +0.070 | +0.048 |
| Haiku | +0.030 | +0.025 |
| OpenJev | +0.060 | -0.007 (noise, no reliable effect) |

**Haiku shows the smallest with/without-key gap of the three arms** --
its own AP World History knowledge is doing almost as much work as
having the literal answer key in front of it (a ~3pp gap vs. Jev's
~5-7pp). Read together with Jev's larger gap, this is a genuine,
decision-relevant finding for an actual grading deployment: Jev leans
more heavily on having a reference answer than Haiku does, consistent
with Jev being a compact, rubric-execution-specialized model rather than
a broad general-knowledge one. OpenJev's whole-exam delta is
statistically indistinguishable from zero -- plausibly a floor effect
given its already-low ~57% whole-exam accuracy leaves little room for the
key to help, though this isn't fully disentangled from genuine
noise/inconsistency at that difficulty level.

**Finding 2 -- a genuine architectural difference: Jev is essentially flat
between chained and whole-exam grading; Haiku and OpenJev both suffer a
large, real accuracy drop in whole-exam mode.**

| Arm | With-key delta (chained - whole_exam) | Without-key delta |
|---|---|---|
| Jev | -0.004 (whole-exam marginally *better*) | -0.025 (whole-exam *better*) |
| Haiku | +0.155 | +0.150 |
| OpenJev | +0.220 | +0.154 |

Jev shows **no meaningful degradation at all** when grading all 30
questions in one call versus one at a time -- if anything, whole-exam
mode is marginally more accurate. Haiku and OpenJev both drop 15-22
percentage points. The most plausible explanation, grounded directly in
the two implementations (not speculation about model quality in the
abstract): Jev's whole-exam call is architecturally **30 independent
`Score` evaluations bundled into one API round-trip** (each with its own
rubric instructions, evaluated in parallel per TypeSafe's own
documentation), essentially identical in kind to 30 separate chained
calls, just cheaper to make. Haiku and OpenJev's whole-exam mode is a
**single shared JSON-generation task** -- one forced tool call that must
hold and correctly reason about all 30 questions' rubrics simultaneously
to fill in one 30-field object. This is a much harder task shape, and the
accuracy drop tracks that difficulty gap closely. This is conceptually
related to CT9's finding that smaller, more isolated units of work
outperform one large bulk call (methodology.md §13) -- but here the
degradation is *avoidable by architecture*, not inherent to the model:
Jev's native multi-question primitive sidesteps the exact problem that
hurts Haiku and OpenJev.

**Total-score MAE (out of 100, mean absolute error per student's summed
graded total vs. true total):**

| Arm | Chained, no key | Chained, with key | Whole-exam, no key | Whole-exam, with key |
|---|---|---|---|---|
| Jev | 5.05 | 3.82 | 4.63 | 3.66 |
| Haiku | 2.90 | 3.86 | 8.84 | 8.32 |
| OpenJev | 7.09 | 6.52 | 9.76 | 10.79 |

Largely confirms Findings 1-2 at the whole-exam-score level (Haiku and
OpenJev's totals get meaningfully less accurate in whole-exam mode; Jev's
stay stable). One genuine curiosity worth flagging rather than
explaining away: **Haiku's chained/without-key total-score MAE (2.90) is
the single best number in this entire table** -- lower than its own
chained/with-key MAE (3.86), despite with-key having the *higher*
per-question exact-match rate (86.2% vs 83.2%). This is possible because
total-score MAE and per-question exact-match are different metrics --
total MAE benefits from error cancellation across 30 questions (an
answer over-scored by 1 point can offset another under-scored by 1),
while exact-match doesn't. This wasn't further diagnosed (would require
per-question error-direction analysis beyond this section's scope) but is
reported as observed rather than smoothed into the general narrative.

**Calibration (chained mode -- the only mode where all three arms report
per-question confidence; Haiku's whole-exam tool schema has no
per-question confidence field, since a single 30-field JSON object isn't
well suited to 30 separate confidence values):**

| Arm | Confidence at errors | Confidence at correct | Gap |
|---|---|---|---|
| Jev | 0.754 (n=977) | 0.915 (n=5,023) | **0.161** |
| Haiku | 0.887 (n=916) | 0.902 (n=5,084) | **0.015** |
| OpenJev | 0.766 (n=1,437) | 0.873 (n=4,563) | **0.107** |

Same ranking as CT5 (§12) and CT9 (§13): Jev's confidence discriminates
correct from incorrect gradings the most sharply, Haiku's the least, on a
third structurally distinct task.

**Cost and latency** (12,000 grade rows per arm: 6,000 chained + 6,000
whole-exam-derived, latency/tokens apportioned evenly across a whole-exam
call's 30 questions for per-row accounting):

| Arm | Avg latency/action | Total cost |
|---|---|---|
| Jev | 102ms | $0.2519 |
| Haiku | 402ms | $10.2225 |
| OpenJev | 238ms | $0.00 |

### Takeaway

CT10 answers the two questions it was built for. On "does the model know
the material without being handed the answer": all three arms benefit
from the key, but Haiku benefits least -- its own historical knowledge is
nearly as good as having the key, a genuinely different profile from
Jev's larger reliance on the reference answer. On "does grading
architecture matter for bulk grading": yes, decisively -- Jev's native
multi-question-per-call primitive lets it grade a full 30-question exam
in one round-trip with no accuracy cost, while both Haiku and OpenJev pay
a real, double-digit-percentage-point accuracy penalty for the same bulk
task, because their single-shared-JSON-object approach to "many answers
in one call" is a fundamentally harder task shape than Jev's parallel
per-question evaluation. The calibration asymmetry first found in CT5 and
confirmed in CT9 replicates a third time, on a task that shares nothing
structurally with either of those two.

## 16. Sonnet 5: revisiting the declined comparison, at full scope

### Motivation

§11 raised a Sonnet 5 comparison as soon as Haiku underperformed Jev on
CT1-4, per prior standing instruction ("if haiku underperforms jev, ask
for more budget to test with sonnet"). The user declined at the time --
verbatim, "if jev did 100%, not worth testing the other stuff. that's
insanely good" -- a reasonable call given the only evidence then was a
clean 100% Jev ceiling on CT1-4. No Sonnet arm was built; Phases 5+
proceeded with jev/haiku/nli-bart/emb-bge, later joined by openjev (§14).

That evidence base changed by the time CT9 (§13) and CT10 (§15) existed.
Both found Haiku underperforming Jev by a *wider* margin than anything in
CT1-8, on structurally different tasks (chained multi-step execution,
partial-credit exam grading) -- exactly the kind of result that would
make a "was this Haiku-specific or general-purpose-LLM-general" check
newly informative, in a way the original CT1-4-only evidence wasn't. The
user asked directly whether Sonnet would do better specifically in the
places Haiku underperformed Jev, then asked for a cost estimate to add
Sonnet as a full fourth arm across the whole benchmark, then approved it:
full scope (CT1-8 + CT9 + CT10, not a reduced subset), matching Haiku's
exact repeat/grid structure for apples-to-apples comparability, and a
budget ceiling of $110 (raised from $50) against a ~$59.34 pre-run cost
projection (derived directly from 2x Haiku's own logged token totals per
task family, since `claude-sonnet-5` is priced at exactly 2x
`claude-haiku-4-5`'s per-token rate on both input and output -- same
projection method used for every prior Sonnet cost estimate in this
project, see §11).

Also requested in the same conversation, done first and separately from
the Sonnet arm itself: reframing this repo's overall narrative from an
"adoption decision" to a neutral benchmark comparison -- removing
prescriptive "Adopt" language from test-plan.md's decision-rule table,
README.md, results.md, and methodology.md's own cross-references, while
preserving the pre-registration structure itself (the point of
pre-registration -- committing to a reading of each outcome before
seeing results -- survives the wording change intact).

### Implementation

Sonnet is architecturally identical to Haiku everywhere it competes --
same rubric text, same forced tool-use pattern, same tool schemas, same
`anthropic.Anthropic()` client, same `record_spend` discipline -- only
the model string and pricing key differ:

- **`arms/sonnet.py`** (new file): CT1-8's `HaikuArm` (`arms/haiku.py`)
  keeps its constants (`MODEL`, `PRICING_KEY`, `SYSTEM_PROMPT`) as
  module-level names referenced directly inside its methods, not via
  `self.X` -- not cleanly subclassable without a prior refactor, so
  `SonnetArm` is a full sibling file, reusing `_build_tool` and
  `_build_user_message` imported directly from `arms/haiku.py` rather
  than duplicating them.
- **`qtree.arms.SonnetChunkArm(HaikuChunkArm)`** and
  **`examgrade.arms.SonnetExamArm(HaikuExamArm)`**: both parent classes
  already read their constants via `self.MODEL`/`self.PRICING_KEY`
  throughout, so these are genuine override-only subclasses -- zero
  method duplication, just `name`/`MODEL`/`PRICING_KEY`/default
  `spend_source` overridden.
- Registry wiring in three independent `_build_arm()` if/elif chains
  (`scripts/run_api_arm.py`, `qtree/runner.py`, `examgrade/runner.py` --
  no central arm registry exists in this codebase) plus their
  `argparse` `choices=[...]` lists.
- `PRICING["claude-sonnet-5"]` already existed in `harness/constants.py`
  (used for corpus-generation cost accounting since Phase 1) and was
  reused as-is for the new arm's pricing key -- same rate, genuinely the
  same model, just a different role (grading/classification instead of
  upstream document authoring).
- Scoring registries updated: `harness.scoring.ALL_KNOWN_ARMS` /
  `CALIBRATION_ARMS` / `source_for_arm`, `qtree.scoring.ARMS`,
  `examgrade.scoring.ARMS` -- all guarded by data-presence checks
  (`load_predictions(arm)` returns `[]` if the file doesn't exist yet),
  safe to land before any Sonnet predictions existed.
- `harness/constants.py`'s `ANTHROPIC_BUDGET_USD` raised $50.00 ->
  $110.00 (and `ANTHROPIC_WARN_USD` $47.00 -> $105.00), with a dated
  rationale comment appended to the existing budget-history narrative,
  matching every prior raise's documentation convention.

Before committing to the full-cost run, each new arm was smoke-tested at
small `--limit` scope (CT1-8: 2 manifest rows -> 24 written; CT9: 2 forms
x k=1 -> 60 chunks; CT10: both chained and whole-exam modes at
`--limit 1/2`) to confirm Sonnet's forced-tool-use behavior matched
Haiku's exactly (it did, no schema incompatibilities) before spending the
full ~$59 projected budget.

### Execution and actual cost

All three full runs (CT1-8: 5,760 calls; CT9: 3,420 chunk calls across
900 traces; CT10: 6,200 calls across chained + whole-exam x with/without
key) were launched concurrently as detached background processes
(`setsid nohup ... </dev/null >log 2>&1 &`, since the combined runtime
was on the order of 3 hours -- far past any single-command timeout) and
polled periodically against `results/predictions/*.jsonl` row counts and
`python -m harness.spend_ledger` until completion, with no manual
intervention required (the existing resumable-append-with-dedup design
in `harness/predictions.py`/`qtree/predictions.py`/`examgrade/predictions.py`
meant the smoke-test rows seamlessly continued into the full run's count
rather than being wasted or needing cleanup).

**Actual final cost came in above the pre-run projection**, by task
family:

| Task | Projected (2x Haiku) | Actual | Over |
|---|---|---|---|
| CT1-8 | $18.36 | $20.7320 | +12.9% |
| CT9 | $20.53 | $24.5497 | +19.6% |
| CT10 | $20.44 | $22.8169 | +11.6% |
| **Total** | **$59.34** | **$68.0986** | **+14.8%** |

The 2x-Haiku-tokens projection assumed Sonnet's token usage would match
Haiku's on identical prompts; in practice Sonnet's real prompts/outputs
ran somewhat larger across all three task families (e.g. CT9's per-call
rate came in at 2.39x Haiku's, not the flat 2.00x pricing multiplier
alone would predict), consistent with a stronger model producing more
verbose internal content even under forced tool-use with a small
`max_tokens` cap. Cumulative Anthropic spend across the whole benchmark
(corpus generation + Haiku + Sonnet) finished at **$109.36 of the
$110.00 approved budget -- $0.64 under the hard cap**, crossing the
$105 warn threshold late in the run (logged, non-blocking warnings only)
but never triggering `BudgetExceeded`. This was closer to the ceiling
than any prior phase of this project and would not have completed if the
approved budget had been set at the bare $59.34 projection with no
margin -- a data point for sizing future cost-projection buffers on this
kind of 2x-multiplier estimate at more like 15-20% headroom, not 0%.

### Findings

Full numeric detail in results.md Part 2 (CT1-8), Part 4 (CT9), and
Part 5 (CT10)'s Sonnet subsections; summarized here by mechanism:

1. **CT1-4: Sonnet ties Jev, both ahead of Haiku** (99.90% vs. Jev's
   100.00%, Haiku's 97.74%) -- the stronger general-purpose model closes
   most, not all, of Haiku's gap on the original, easier corpus.
2. **CT5-8: Sonnet is the *worst* of the three, not the best** (92.47%
   vs. Jev's 97.67%, Haiku's 95.17%), driven almost entirely by one
   isolated cell: **CT7 (multi-hop lookup) under Condition C (misleading
   folder names) collapses to 34.4%**, a 65.6-point drop from every other
   CT7 cell, where Jev and Haiku both stay at 100.00%. This is genuinely
   new information CT1-4-scope testing never surfaced: CT7 was originally
   hypothesized to be a Jev weakness (multi-hop reasoning favoring
   autoregressive generation over a single forward pass, test-plan.md
   §4) and never materialized for Jev *or* Haiku -- it turns out to be
   Sonnet's single sharpest failure in the entire suite. Mechanism
   evidence points toward the same label-collision pattern independently
   diagnosed for OpenJev on the identical cell (§14): errors are
   high-confidence (0.947 mean, indistinguishable from the 0.941 mean at
   correct predictions on the same cell) and not consistently biased
   toward one wrong folder across repeats, and the identical tree scores
   100% under SHUFFLE (opaque ids) -- ruling out "Sonnet can't do
   multi-hop lookup" in general, isolating it to misleading-but-plausible
   real names specifically, same as OpenJev.
3. **CT9: Sonnet crosses both other models' lines, in opposite
   directions, as chunk size k grows.** Best of the three at k=1 (86.7%,
   +11.7pp over Jev, +28.9pp over Haiku) -- the strongest single-step
   reasoner wins decisively at the narrowest possible decision. Worst of
   the three at k=10 (22.8%, below Jev's 29.4-33.9% and Haiku's 31.7%) --
   added capability did not help it hold up through one large, unassisted
   multi-step trace; if anything, it degraded faster. Also the single
   least-stable result anywhere in this project: 20.0% run-to-run
   disagreement at k=10 under opaque labeling (vs. 3.3% under semantic
   labeling for Sonnet itself, and Jev's worst of 8.3-10%, Haiku's 0%).
4. **CT10: the sharpest, most decision-relevant Sonnet finding in the
   whole benchmark.** In chained-with-key mode, Sonnet is the best grader
   of all four models by a wide margin (MAE 0.039, 96.1% exact-match,
   total-exam-score error 0.93 points -- better than Jev's 3.82 and
   Haiku's 3.86). In whole-exam mode, the exact same underlying knowledge
   batched into one 30-question call, it becomes the *worst* grader of
   all four (MAE 0.44-0.57, total-exam-score error up to 16.44 points --
   roughly 3.6x Jev's and 1.9x Haiku's). The drop from chained to
   whole-exam (36 points of exact-match rate) is more than double either
   Haiku's (15pp) or OpenJev's (19pp) architecture-driven degradation
   (§15's finding, replicated and sharpened). Same model, same rubric,
   same students -- the only variable that moved is how many judgments it
   held in one call, and on that axis alone it went from best to worst.
   Confidence does not flag this: Sonnet's chained-mode confidence gap
   (0.070) is small, and whole-exam mode has no per-question confidence
   field to check at all.
5. **Calibration, replicated a fourth way**: Sonnet's confidence-at-errors
   is close to its confidence-at-correct on every task (CT1-8 gap 0.0097,
   CT9 gap 0.039, CT10 chained gap 0.070) -- the same "fails confidently"
   pattern as Haiku, not meaningfully better despite being the stronger
   model. Jev remains the only arm whose confidence is a decision-usable
   signal for a review queue.

### Takeaway

The net effect on Part 2's comparison (test-plan.md §6) is unchanged from
§11's original conclusion -- Jev remains ahead of both Claude models on
accuracy, at 50-116x lower price. What changed is the texture of *why*:
Sonnet does not simply "do better than Haiku" in the places Haiku
underperformed Jev, which was the question that motivated revisiting this
comparison in the first place. It does dramatically better in some narrow
slices (CT9 k=1, CT10 chained-with-key) and dramatically worse in others
(CT1-8's CT7/Condition-C, CT9 k=10, CT10 whole-exam) -- a stronger
general-purpose model traded one failure profile for a different, more
isolated one, rather than uniformly closing the gap. This is exactly the
kind of result a benchmark limited to Haiku alone, or one that stopped
after the original CT1-4-only evidence, would never have found.
