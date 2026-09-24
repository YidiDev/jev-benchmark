# Jev Benchmark: Rubric-Based Zero-Shot Classification, Chained Execution & Exam Grading

**Does [Jev](https://typesafe.ai) (TypeSafe AI's rubric-conditioned classification model) genuinely
read and apply a multi-clause rubric — and how does it stack up against two general-purpose LLMs
(Claude Haiku 4.5, Claude Sonnet 5) and a free, self-hostable alternative (OpenJev), on both
quality *and* price?**

This repo is the full benchmark: every corpus, every prediction, every dollar spent, every test
that failed to find a difference as well as every one that did. Ten structurally distinct test
suites, four models, **124 passing tests**, **$110.11 total spend**, all of it reproducible from
the seeds and scripts in this repo.

<p align="center">
  <img src="charts/10_accuracy_vs_cost.png" width="640" alt="Accuracy vs. cost: Jev is both more accurate and ~50x cheaper than Claude Haiku 4.5">
</p>

## TL;DR

| | Jev | Claude Haiku 4.5 | Claude Sonnet 5 | OpenJev |
|---|---|---|---|---|
| **CT1-8 overall accuracy** | **98.84%** | 96.46% | 96.18% | 96.28% |
| **Price per 1,000 calls (CT1-8)** | $0.031 | $1.590 | $3.599 | **~$0.014 (self-hosted est.)** |
| **Total spend, whole benchmark** | $0.75 | $29.67 | $68.10 | **$0.00 real / ~$0.43 self-hosted est.** |
| Calibration (confidence flags real errors) | **Consistently useful, 3/3 tasks** | Consistently useless, 3/3 tasks | Consistently useless, 3/3 tasks | In between |

OpenJev's real spend in this benchmark genuinely was $0.00 (Codiv's free hosted tier) — the
"self-hosted est." figures are a documented estimate of what running it yourself on rented GPU
compute would cost instead, so it isn't compared against metered API arms as if it were free to
deploy. See [Price, in full](#price-in-full) and [methodology.md §17](./methodology.md#17-estimating-self-hosted-compute-cost-for-the-free-arms)
for the exact assumptions.

**Jev is both more accurate and ~50-116x cheaper than the two Claude models on the core
classification task** — the single clearest number in this repo. It also wins on rubric-following
under adversarial relabeling, on the specific arithmetic weakness its own vendor documentation
predicted, and on calibration (its confidence scores actually flag its mistakes; neither Claude
model's do). Its advantages are *not* universal, though — they concentrate specifically where task
structure favors Jev's architecture (small-step execution, native multi-question batching) and
disappear where it doesn't.

**The most surprising result belongs to Sonnet, not Jev.** Anthropic's *stronger* model was added
specifically to check whether Haiku's underperformance was a Haiku-specific weakness or a
general-purpose-LLM one. It's neither, cleanly — Sonnet is the best of all four models at the
narrowest, most focused version of every task (single document, single question, one decision
step at a time) and the *worst* of all four at the broadest, most batched version of the same
tasks (30-question whole-exam grading, full 10-layer tree traversal in one call). More capability
did not transfer into more reliable batching; if anything, the opposite. Read on for the receipts.

---

## Table of contents

1. [What this benchmark answers, and why](#what-this-benchmark-answers-and-why)
2. [Models under test](#models-under-test)
3. [The ten test suites](#the-ten-test-suites)
4. [Results, part by part](#results-part-by-part)
   - [Part 1 — Does Jev genuinely read the rubric?](#part-1--does-jev-genuinely-read-the-rubric)
   - [Part 2 — Jev vs. two Claude models: head-to-head comparison](#part-2--jev-vs-two-claude-models-head-to-head-comparison)
   - [Part 3 — OpenJev fallback viability](#part-3--openjev-fallback-viability)
   - [Part 4 — CT9: chained decision-tree execution](#part-4--ct9-chained-decision-tree-execution)
   - [Part 5 — CT10: AP World History exam grading](#part-5--ct10-ap-world-history-exam-grading)
   - [Calibration, across every task](#calibration-across-every-task)
5. [Price, in full](#price-in-full)
6. [Methodology highlights](#methodology-highlights)
7. [Reproducing this benchmark](#reproducing-this-benchmark)
8. [Repository layout](#repository-layout)
9. [Full documentation](#full-documentation)
10. [License](#license)

---

## What this benchmark answers, and why

Most "zero-shot classification" benchmarks test whether a model can match a label's *text* to a
document's *content* (NLI entailment, embedding similarity). That's a different, easier task than
what a real rubric-based sorting system needs: **conditioning on an arbitrary, multi-clause set of
rules** — thresholds, exceptions, lookups, negations — regardless of what the destination folders
happen to be named.

This benchmark was built to answer five concrete questions, in order:

1. **Does Jev genuinely condition on the rubric**, or is it secretly doing label-text matching
   like a classifier would? (Part 1 — tested via an adversarial shuffle control.)
2. **Is Jev good enough to replace a cheap general-purpose LLM** for this task, on quality *and*
   price? (Part 2 — Claude Haiku 4.5 as the reference ceiling.)
3. **Is there a viable, free, self-hostable fallback** if Jev's hosted API ever became
   unavailable? (Part 3 — OpenJev, an open-weights model that speaks Jev's exact wire protocol.)
4. **Where does Jev actually break?** A benchmark where the subject scores 100% tells you
   nothing about its limits — so four "hard mode" clause types (Part 2) and a completely
   different task, chained multi-step decision execution (Part 4, CT9), were built specifically
   to find failure modes.
5. **Does any of this generalize to a genuinely different task shape** — partial-credit rubric
   grading of open-ended text, not classification? (Part 5, CT10.)

Every design decision below — the seeded-RNG discipline, the shuffle control, the price ledger,
the decision to build *harder* tests once the easy ones stopped being informative — is documented
with its rationale in [`methodology.md`](./methodology.md), including the places where an initial
approach turned out to be wrong and was replaced.

## Models under test

| Model | What it is | Pricing (list) |
|---|---|---|
| **Jev** (`jev-1.13`) | TypeSafe AI's purpose-built rubric-classification model. Three primitives: `Noul` (yes/no), `Choice` (pick 1 of ≤255 options), `Score` (rate against an ordered rubric). | $0.042 / Mtok input, **output free** |
| **Claude Haiku 4.5** | Anthropic's fast general-purpose LLM — the reference-ceiling comparison arm. | $1 / Mtok input, $5 / Mtok output |
| **Claude Sonnet 5** | Anthropic's stronger general-purpose LLM, added later to check whether Haiku's underperformance was Haiku-specific or general — same rubric, same forced tool-use, same grid as Haiku throughout. | $2 / Mtok input, $10 / Mtok output |
| **OpenJev** | `razorback16/openjev`, an open-weights model (DiffusionGemma 26B-A4B, Apache-2.0) that speaks Jev's exact wire API. Tested via the free-hosted [Codiv](https://codiv.ai) endpoint — real cost here is $0.00, but self-hosting it (its actual real-world deployment path) is estimated at ~$0.028/Mtok input on a 24GB-class GPU. | **$0.00** (hosted tier used) / ~$0.028/Mtok (self-hosted est.) |
| NLI (bart-large-mnli) / Embeddings (bge-m3) | Standard zero-shot classification baselines — the "does it actually read the rubric" control group for Part 1. Not real contenders (they can't follow a rubric at all), included to prove the point. Ran locally in this benchmark (real cost $0.00); self-hosting either commercially is estimated at ~$0.03/Mtok on a small cloud GPU. | Local, **$0.00** real / ~$0.03/Mtok (self-hosted est.) |

## The ten test suites

| Suite | Tests | Ground truth |
|---|---|---|
| CT1 descriptive | Simple 3-way document type sort | Structured metadata |
| CT2 conjunctive+threshold | Numeric threshold rule | Structured metadata |
| CT3 relational | Lookup + override exception | Structured metadata |
| CT4 negative/exclusionary | Negation-based rule | Structured metadata |
| CT5 computed_threshold | **Arithmetic**: sum stated line items, no total given | Structured metadata |
| CT6 temporal_reasoning | Date comparison, zero narrative cues | Structured metadata |
| CT7 multi_hop_relational | Two chained lookups (team → division → program) | Structured metadata |
| CT8 long_context_distractor | Same logic as CT1, buried in ~600-word padding | Structured metadata |
| CT9 chained decision execution | 10-layer decision tree, walked in 1/2/5/10-step chunks, 4 outcome folders | Code-computed tree walk |
| CT10 exam grading | Partial-credit rubric grading of 30 AP World History paragraph answers, 100 students | Seeded student-ability model |

CT1-4 is the original design. CT5-8 ("hard mode") and CT9/CT10 were built afterward, specifically
because CT1-4 turned out to be a ceiling task (Jev: 100%) — a benchmark that never finds a failure
can't characterize one.

---

## Results, part by part

### Part 1 — Does Jev genuinely read the rubric?

<p align="center"><img src="charts/01_shuffle_control.png" width="560"></p>

The critical test: **Condition C** relabels folders with *misleading* but semantically real names
(a text-matcher's worst case), and the **SHUFFLE control** adversarially permutes the
rubric-clause-to-folder-ID mapping under opaque IDs. If Jev were secretly doing label-text
matching, its accuracy under these conditions would collapse toward the NLI/embedding baselines.
**It doesn't — Jev stays at 100.00% in every single condition**, while the baselines collapse to
26-48%. This is the foundational result everything else builds on.

**Price**: this part's baselines ran locally in this benchmark, real cost $0.00 — CT1-4 corpus
generation cost **$1.06** total (one-time Sonnet 5 cost to build the 240-document corpus), Jev's
own inference cost **$0.18** for all 2,880 classifications, and NLI/embeddings' estimated
self-hosted cost (if you deployed them instead of running locally like this benchmark did) is
**~$0.03 and ~$0.01** respectively for the same 1,440 real predictions each — see
[methodology.md §17](./methodology.md#17-estimating-self-hosted-compute-cost-for-the-free-arms).

### Part 2 — Jev vs. two Claude models: head-to-head comparison

<p align="center"><img src="charts/02_overall_accuracy.png" width="560"></p>

| | Jev | Haiku | Sonnet |
|---|---|---|---|
| CT1-4 (original corpus) | **100.00%** | 97.74% | 99.86% |
| CT5-8 (hard mode, built to find Jev's limits) | **97.67%** | 95.17% | 92.50% |
| **Price, CT1-4 + CT5-8 combined (5,760 calls)** | **$0.18** | $9.18 | $20.73 |

**Jev wins on both accuracy and price against both Claude models**, by a wide margin on price
(**~50-116x cheaper**). Sonnet was added later specifically because Haiku underperformed Jev by a
wider margin on CT9/CT10 than on CT1-8 — the question was whether a stronger model would close
the gap. On CT1-4 it nearly does (99.86%, within noise of Jev's 100%). **On CT5-8 it doesn't — it's
the worst of the three**, and for a different reason than Haiku's. Digging into *why* CT5-8 exists:

<p align="center"><img src="charts/03_ct5_arithmetic.png" width="480"></p>

Jev's one real weakness anywhere in CT1-8 — arithmetic near a stated threshold — was predicted in
advance by the vendor's own model documentation. It's real (9.3% error rate), and **both Claude
models are worse at it** (Haiku 18.2%, Sonnet 13.7%). But CT5 arithmetic isn't what drags Sonnet's
CT5-8 average down the most — **Sonnet has an isolated, severe failure on CT7's two-hop lookup
under Condition C** (misleading-but-plausible folder names) that neither Jev nor Haiku share at
all: accuracy collapses from 100% (every other condition) to **34.4%**, at *high* confidence
(0.95 mean, indistinguishable from its confidence when correct) — see [Part 3](#part-3--openjev-fallback-viability)'s
chart, which now shows this side-by-side with OpenJev's own, independently-diagnosed collapse on
the exact same clause type and condition. Two of the three a priori predicted weaknesses
(multi-hop lookup, long-context distraction) materialize for *exactly one* model each (Sonnet on
CT7, nobody on CT8) — reported as found, not smoothed into an average.

**Result, per the pre-registered comparison rule in [`test-plan.md`](./test-plan.md): Jev matches
or exceeds both Claude models on accuracy** in every scope tested, at 50-116x lower price — a wide
margin on both axes of the comparison. Being the *stronger* general-purpose model did not help
Sonnet here; it has a sharper, more isolated failure mode than Haiku, not a smaller one.

### Part 3 — OpenJev fallback viability

<p align="center"><img src="charts/04_ct7_openjev_collapse.png" width="640"></p>

OpenJev cost $0.00 in this benchmark (free Codiv hosted tier) and scores 96.28% overall on CT1-8 —
a genuinely viable, low-cost fallback for simple classification (self-hosting it for real is
estimated at ~$0.014 per 1,000 calls on CT1-8, still 2-100x cheaper than every other arm — see
[Price, in full](#price-in-full)). It has exactly one sharp, fully-diagnosed weakness: CT7's multi-hop lookup
collapses to 40% under Condition C specifically (red bar above) — but the *identical* tree scores
100% under the SHUFFLE control (opaque random IDs). That rules out "OpenJev can't follow the
rubric" — it's a label-*collision* bug (Condition C's misleading names are other real, plausible
labels; SHUFFLE's aren't), isolated to one clause type under one condition. **Sonnet (violet bar)
independently collapses on the exact same clause type and condition**, to a similar 34.4% — two
structurally different models, hitting the same specific trap, for what looks like the same
underlying reason (both fail confidently, and both recover completely under SHUFFLE).

**Price**: $0.00 real spend, always — the free Codiv tier never touched the $110 Anthropic budget
for any of CT1-8, CT9, or CT10. Self-hosting it for real is estimated at **$0.43 total** across
all three task families (methodology.md §17) — still far below every metered API arm, but not
actually free the way "$0.00" implies.

**Verdict**: viable low-cost fallback for CT1-8-style classification; not yet viable for CT9-style
chained execution (see below) — meaningfully behind all three other models at every step size.

### Part 4 — CT9: chained decision-tree execution

<p align="center"><img src="charts/05_ct9_k_curve.png" width="600"></p>

A completely different task from CT1-8: walking a 10-layer decision tree in chunks of size
k ∈ {1, 2, 5, 10}, with **real compounding** between chunks (no ground-truth rescue). The
headline finding inverts the a priori hypothesis: going in, more handoffs (lower k) was expected
to *hurt* accuracy via compounding error. **It's the opposite for every model** — frequent small
handoffs beat one unassisted full-chain call, decisively.

**Jev's advantage over Haiku is real but narrow**: +17-22pp at k=1/2, but statistically tied at
k=5/10 — Jev's edge is about small-step execution discipline, not raw multi-hop reasoning
capacity. **Sonnet crosses both other lines, in opposite directions, as k grows.** At k=1 it's the
best of all three (86.7%, +11.7pp over Jev, +28.9pp over Haiku) — the strongest model wins
decisively at the narrowest possible decision. By k=10 it's the *worst* of all three (22.8% vs.
Jev's 29.4% and Haiku's 31.7%) — more capability did not help it hold up under one large,
unassisted, multi-step call; if anything it degraded faster than either weaker model. **The one
place in this whole benchmark where Jev is *less* stable than Haiku**: at k=10, Jev disagrees with
itself across repeats 8.3-10% of the time vs. Haiku's 0% — but Sonnet is less stable still at k=10
under opaque labeling (20%), the highest disagreement rate anywhere in this project. Reported as
found, not smoothed over.

**Price**: 900 traces × 4 arms = 3,420 API calls per model. Jev **$0.32**, Haiku **$10.27**,
Sonnet **$24.55**, OpenJev $0.00 real / ~$0.20 self-hosted est. — both Jev and a self-hosted
OpenJev undercut both Claude models by more than two orders of magnitude on this much more
demanding multi-step task (see [Price, in full](#price-in-full)).

### Part 5 — CT10: AP World History exam grading

<p align="center"><img src="charts/06_ct10_chained_vs_whole_exam.png" width="600"></p>

A third structurally distinct task: partial-credit rubric grading of open-ended paragraph
answers (30 questions, 100 simulated students, non-uniform rubric summing to 100 points), with an
orthogonal axis — does the grading model need the answer key, or does it already know the
material? Two grading modes: **chained** (1 call/question) and **whole-exam** (1 call, all 30
questions at once).

**A genuine architecture-driven finding**: Jev is essentially flat between chained and whole-exam
grading (its `system_one` call natively evaluates multiple `Score` questions in parallel, so its
"whole exam" call is structurally ~30 independent judgments). **Haiku, Sonnet, and OpenJev all
lose ground in whole-exam mode** — their single-shared-JSON-object approach to "many answers in
one call" is a genuinely harder task shape. This is avoidable by architecture, not an inherent
model-quality gap. **Sonnet loses by far the most: 90% → 54% exact-match, a 36-point drop** —
more than double Haiku's 15pp drop and OpenJev's 19pp drop.

**This is the sharpest, most decision-relevant Sonnet result in the whole benchmark.** In
*chained-with-key* mode, Sonnet is the best grader of all four models by a wide margin — MAE
0.039 (96.1% exact-match) vs. Jev's 0.129 and Haiku's 0.139, and total-exam-score error of just
0.93 points vs. Jev's 3.82 and Haiku's 3.86. Ask it one focused question at a time, with the
answer key, and it's clearly the strongest grader here. But in *whole-exam* mode — the exact same
underlying knowledge, batched into one 30-question call — it becomes the **worst** grader of all
four: MAE 0.44-0.57 (vs. Haiku's 0.30-0.33 and Jev's 0.12-0.17), total-exam-score error up to
16.44 points (vs. Haiku's 8.84, Jev's 4.63). Same model, same material, same rubric — the only
variable that moved is how many judgments it had to hold in one call, and on that axis alone it
went from best to worst. Confidence doesn't flag this either: Sonnet's confidence-at-errors
(0.839) is barely below its confidence-at-correct (0.909), the same "fails confidently" pattern
as Haiku, just less extreme.

On the knowledge question: **Haiku needs the answer key the least** in chained mode (its own
historical knowledge does almost as much work as being handed the key, +2.5-3pp gap vs. Jev's
+5-7pp) — Sonnet needs it *the most* (+13pp chained exact-match gap between with/without key,
the largest of the three LLM arms) — a genuinely different profile from the accuracy/price story
above.

**Price**: 6,200 grading actions × 4 arms = 24,800 calls. Jev **$0.25**, Haiku **$10.22**,
Sonnet **$22.82**, OpenJev $0.00 real / ~$0.15 self-hosted est.

### Calibration, across every task

<p align="center"><img src="charts/07_calibration.png" width="620"></p>

The single most decision-relevant number in this whole repo, replicated on **three structurally
unrelated tasks**: does a model's confidence actually predict whether it's wrong? **Jev's does,
consistently.** Both Claude models' confidence is nearly flat between correct and incorrect
answers — they fail *confidently*, giving a downstream review queue nothing to act on. Sonnet's
gap (0.01-0.07 across the three tasks) is marginally larger than Haiku's (0.00-0.05) but nowhere
close to Jev's (0.16-0.49) — being a stronger model didn't make Sonnet's confidence more useful,
either. A rule like "route anything under 0.6 confidence to human review" would catch the large
majority of Jev's mistakes; the equivalent rule for either Claude model would catch almost none of
them.

---

## Price, in full

Price is a first-class result in this benchmark, not an afterthought — every table above includes
it, and here's the full picture:

<p align="center">
  <img src="charts/09_cost_per_1000_calls.png" width="560">
  <img src="charts/08_cost.png" width="400">
</p>

| Model | CT1-8 (5,760 calls) | CT9 (3,420 calls) | CT10 (~6,200 calls) | **Total, all arms** |
|---|---|---|---|---|
| Jev | $0.18 | $0.32 | $0.25 | **$0.75** |
| Claude Haiku 4.5 | $9.18 | $10.27 | $10.22 | **$29.67** |
| Claude Sonnet 5 | $20.73 | $24.55 | $22.82 | **$68.10** |
| OpenJev, real spend | $0.00 | $0.00 | $0.00 | **$0.00** |
| OpenJev, self-hosted estimate | ~$0.08 | ~$0.20 | ~$0.15 | **~$0.43** |
| NLI (bart-large-mnli), self-hosted estimate | ~$0.03 | — | — | **~$0.03** |
| Embeddings (bge-m3), self-hosted estimate | ~$0.01 | — | — | **~$0.01** |

**Two different numbers, deliberately kept apart.** OpenJev's row above genuinely cost $0.00 in
this benchmark (Codiv's free hosted tier), and NLI/embeddings genuinely cost $0.00 too (ran
locally on this project's own hardware) — that's the real, metered spend, unchanged in
`results/spend_ledger.jsonl`. The "self-hosted estimate" rows are a separate, documented
projection of what actually deploying each of these three yourself would cost on rented GPU
compute (methodology.md §17) — not real spend, and never counted against the Anthropic budget
below. Even under that estimate, Jev and a self-hosted OpenJev both still cost under 1% of the
two Claude models' combined spend across the entire benchmark — Jev is not the *cheapest* option
by this estimate on any single task family (OpenJev's self-hosted estimate undercuts it
everywhere, a genuinely counterintuitive result explained in methodology.md §17), but both remain
in a completely different cost class from either Claude model.

Corpus generation (one-time, via Claude Sonnet 5 in its upstream content-authoring role — not the
same as its downstream grading-arm role above — to build the 480 CT1-8 documents + 60 CT9 forms +
100 CT10 exams) cost an additional $11.59 — not a recurring cost, since the corpus itself is
committed to this repo and never needs regenerating. **Grand total (real, metered spend):
$110.11**, all logged to [`results/spend_ledger.jsonl`](./results/spend_ledger.jsonl) call-by-call
as it was spent, not estimated after the fact — cumulative Anthropic spend (corpus generation +
Haiku + Sonnet) landed at $109.36 of the $110.00 approved budget, $0.64 under the hard cap.

## Methodology highlights

Full detail in [`methodology.md`](./methodology.md) (17 sections, one per phase); the highlights
that matter most for trusting these results:

- **Seeded RNG discipline.** Every choice that should be uninfluenced by semantics — opaque folder
  IDs, the shuffle-control permutation, which criteria a partial-credit answer satisfies, student
  ability — is drawn from `harness.constants.sub_rng(purpose)`, an independently-reproducible
  stream keyed off one `MASTER_SEED`. Nothing here was hand-picked to look good.
- **The shuffle control** (Part 1) is the load-bearing methodological device of this whole
  project: it's the one test that can actually distinguish "the model reads the rubric" from "the
  model matches folder-name vibes," and it was applied to every classification-shaped task.
- **Price tracked as it was spent**, not estimated afterward — every API call, successful or not,
  is logged to `results/spend_ledger.jsonl` with a hard budget ceiling enforced *before* the call
  that would exceed it, not after. Real spend for nli-bart/emb-bge/OpenJev genuinely is $0.00 in
  this ledger — the separate self-hosted cost estimate (methodology.md §17) is exactly that,
  clearly labeled and never mixed into the real ledger, precisely because this principle matters.
- **Negative results are reported, not hidden.** CT7 and CT8 (hard mode) found no weakness for
  Jev or Haiku (Sonnet is the exception on CT7 — also reported, not smoothed over). CT9 found
  Jev *less* stable than Haiku at k=10, and Sonnet less stable still. All of it is in the numbers
  above, not filtered out.
- **Decomposition frozen up front** (test-plan.md §8): rubric-clause granularity is a large free
  parameter that can make a task look artificially easy or hard; the exact decomposition is fixed
  before any arm sees the test set and applied identically across every arm.
- **A comparison arm added after the fact, reasoned about openly.** Sonnet was proposed, declined,
  and later revisited once CT9/CT10 existed and showed Haiku underperforming Jev by a wider margin
  than CT1-8 ever did — the reversal and its cost accounting are logged in methodology.md, not
  presented as though Sonnet had been in scope from the start.

## Reproducing this benchmark

```bash
uv sync
cp .env.example .env   # fill in TYPESAFE_API_KEY, ANTHROPIC_API_KEY, CODIV_API_KEY

# Everything below is already committed (corpus, predictions, spend ledger) --
# these commands regenerate results from what's already here, or extend it.
pytest tests/ -q                        # 124 tests, exercises every scoring function
python -m harness.spend_ledger          # print the full price ledger (real, metered spend)
python -m scripts.estimate_self_hosted_cost  # rebuild results/self_hosted_cost_estimate.json
python -m scripts.generate_summary      # rebuild results/summary.{json,csv}
python -m scripts.generate_charts       # rebuild every chart in charts/

# Re-running an arm against already-generated corpora (resumable, will skip
# anything already in results/predictions/):
python -m scripts.run_arm --arm nli-bart
python -m scripts.run_api_arm --arm jev        # or haiku / sonnet / openjev
python -m qtree.runner --arm jev               # CT9
python -m examgrade.runner --arm jev           # CT10
```

Regenerating the corpus from scratch (not needed — it's committed — but fully reproducible):
`corpus/generate_metadata.py` → `corpus/generate_prose.py` (and the `qtree`/`examgrade`
equivalents), all seeded from `MASTER_SEED` in `harness/constants.py`.

## Repository layout

```
corpus/       CT1-8 document generator + frozen manifest + ground-truth engine
rubrics/      Rubric clause text, folder-name conditions, shuffle-control permutation
arms/         One module per CT1-8 arm: jev, haiku, sonnet, openjev, nli-bart, emb-bge
qtree/        CT9: decision tree, chunked execution arms, scoring
examgrade/    CT10: exam questions/rubrics, student corpus, grading arms, scoring
harness/      Shared scoring (bootstrap CI, ECE, disagreement), spend ledger, constants
scripts/      run_arm / run_api_arm (CT1-8), generate_summary, generate_charts,
              estimate_self_hosted_cost
results/      Every raw prediction, the spend ledger, the self-hosted cost
              estimate, and the consolidated summary
charts/       Every chart in this README, regenerable via scripts/generate_charts.py
tests/        124 tests covering ground truth, RNG determinism, and every scoring function
```

## Full documentation

- [`test-plan.md`](./test-plan.md) — the original design document (written before any code existed)
- [`methodology.md`](./methodology.md) — every decision made, in order, including what didn't work
- [`results.md`](./results.md) — the full numeric results this README summarizes
- [`results/summary.json`](./results/summary.json) / [`results/summary.csv`](./results/summary.csv) — every computed metric, machine-readable

## License

[MIT](./LICENSE).
