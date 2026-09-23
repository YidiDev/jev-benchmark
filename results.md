# Results — Rubric-Based Zero-Shot Classification Model Benchmark

Living document. Filled in as runs complete. See [`methodology.md`](./methodology.md)
for how these numbers were produced and [`test-plan.md`](./test-plan.md) for
the design these results answer.

Status: **Corpus complete: 480 docs across 8 clause types (CT1-4 original +
CT5-8 "hard mode," see [`methodology.md` §12](./methodology.md#12-hard-mode-ct5-ct8)).
All four built arms (jev, haiku, nli-bart, emb-bge) have completed full
3-repeat × 4-condition runs (including the shuffle control) across all 8
clause types. Scoring harness (`harness/scoring.py`) built: bootstrap 95%
CIs, calibration ECE (raw + temperature-fit), shuffle delta, confidence-at-
errors, disagreement, cost/latency. OpenJev (Part 3) still pending
`CODIV_API_KEY`.**

---

## Part 1 — Does Jev condition on the rubric? (vs NLI)

**Answer: yes, unambiguously.** Accuracy over the original 240-doc corpus
(CT1-4) × 3 repeats. Jev's 95% bootstrap CI is [1.000, 1.000] in every
cell (zero errors, zero variance to bootstrap) — see
`harness.scoring.accuracy_table("jev")` for the full table with CIs for
every arm/clause-type/condition combination.

### Accuracy per (condition × clause type) — raw, pre-bootstrap

| Clause type | nli-bart A | nli-bart B | nli-bart C | emb-bge A | emb-bge B | emb-bge C | **jev A** | **jev B** | **jev C** | **jev SHUFFLE** |
|---|---|---|---|---|---|---|---|---|---|---|
| CT1 descriptive | 1.00 | 0.30 | 0.00 | 0.77 | 0.35 | 0.07 | **1.00** | **1.00** | **1.00** | **1.00** |
| CT2 conjunctive+threshold | 0.65 | 0.57 | 0.35 | 0.53 | 0.37 | 0.47 | **1.00** | **1.00** | **1.00** | **1.00** |
| CT3 relational | 0.37 | 0.37 | 0.28 | 0.47 | 0.32 | 0.22 | **1.00** | **1.00** | **1.00** | **1.00** |
| CT4 negative/exclusionary | 0.58 | 0.50 | 0.42 | 0.52 | 0.50 | 0.48 | **1.00** | **1.00** | **1.00** | **1.00** |

NLI-bart and emb-bge behave exactly as the design predicts: strong on
Condition A (folder name carries real signal), collapsing toward or below
chance on B (opaque ids, no signal) and C (misleading — same label text as
A, wrong folder, so a text matcher is *confidently wrong*). Jev is at
ceiling (1.00) in every cell, including C and SHUFFLE.

### Shuffle-control delta

**0.00 delta — Jev tracks the permuted rubric perfectly**, which is the
specific, falsifiable signature test-plan.md §5.1 asks for: if Jev were
using semantic content priors instead of genuinely reading the rubric, it
would keep landing on the "obviously correct" folder and its accuracy
against the *shuffled* answer key would collapse toward the label-text
baselines above (or toward 0, per the derangement argument in
methodology.md §10). Instead it stays at 1.00 under an adversarially
permuted clause-to-folder-id mapping. See methodology.md §10 for the
incident where an earlier (incorrect) implementation of this control
produced a false failure signal, and the fix.

Caveat carried into Part 2: Jev is at ceiling on this corpus, so this
benchmark alone cannot yet distinguish "Jev is extremely capable at this
task" from "this corpus's hardest cases are still easy for any competent
model" — that question is deferred to the Haiku comparison.

## Part 2 — Does Jev match Haiku 4.5 on quality? (head-to-head comparison)

**Answer: no, Jev beats Haiku, on both the original corpus and the
hard-mode corpus designed to break it.** CT1-4 (full 3-repeat scope, both
arms): Jev 100.00% (2,880/2,880). Haiku 97.74% (2,815/2,880). CT5-8
"hard mode" (full 3-repeat scope, both arms, see
[methodology.md §12](./methodology.md#12-hard-mode-ct5-ct8)): Jev 97.67%
(2,813/2,880). Haiku 95.17% (2,741/2,880).

### Accuracy per (condition × clause type) — CT1-4, both arms at full 3 repeats

| Clause type | jev A | jev B | jev C | jev SHUFFLE | haiku A | haiku B | haiku C | haiku SHUFFLE |
|---|---|---|---|---|---|---|---|---|
| CT1 descriptive | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.97 | 1.00 |
| CT2 conjunctive+threshold | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 | 1.00 |
| CT3 relational | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 0.93 | 0.92 | 0.92 |
| CT4 negative/exclusionary | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 |

**85% of Haiku's CT1-4 errors (55/65) are CT3 relational-lookup failures
with a single, consistent mechanism**: confusing a non-retainer distractor
client name for a real retainer-list client because they share a prefix
word (e.g. "Anchor Robotics" → wrongly treated as retainer "Anchor
Materials"), at high confidence (0.95–1.00). Jev resolves the identical
documents correctly (manually spot-checked). See methodology.md §11.

### Accuracy per (condition × clause type) — CT5-8 "hard mode," both arms at full 3 repeats

| Clause type | jev A | jev B | jev C | jev SHUFFLE | haiku A | haiku B | haiku C | haiku SHUFFLE |
|---|---|---|---|---|---|---|---|---|
| CT5 computed_threshold (arithmetic) | 0.91 | 0.92 | 0.89 | 0.91 | 0.83 | 0.82 | 0.81 | 0.81 |
| CT6 temporal_reasoning (dates) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.96 | 1.00 |
| CT7 multi_hop_relational | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| CT8 long_context_distractor | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Jev has one real, isolated weakness: CT5 arithmetic near the $5,000
threshold** (67/720 errors, 100% within $300 of the threshold, 66/67
biased toward overestimating the sum). **Haiku has the same weakness, but
worse** (131/720 errors, ~2x Jev's rate, and flat across conditions rather
than concentrated by numeric distance). **CT7 and CT8 were not
differentiating** — both arms scored 100.00% in every cell, contradicting
the a priori expectation that multi-hop lookup and long-context distraction
would be hard for Jev. **CT6 surfaces a second flavor of content-prior
contamination in Haiku, absent in Jev**: under Condition C's label swap,
Haiku correctly determines the date relationship in all 8 of its errors but
then outputs the folder name that *sounds* semantically right rather than
the one the rubric's permuted mapping actually specifies (confidence
0.95–1.00 every time). Jev shows zero such errors across all 8 clause
types. Full mechanism writeups: methodology.md §12, Findings 1-3.

### Calibration (ECE, raw and temperature-fit)

Full corpus (all 8 clause types), temperature fit on the validation split
(n=960), evaluated on the test split (n=4,800):

| Arm | Raw ECE | Fitted T | Fitted ECE |
|---|---|---|---|
| Jev | 0.0331 | 0.20 | 0.0112 |
| Haiku | 0.0098 | 1.00 (no improvement) | 0.0098 |

Haiku's raw ECE looks *better* in aggregate — but this is exactly the
metric test-plan.md warns is insufficient alone: Haiku is mostly very
confident and mostly correct, which flatters an aggregate calibration
curve while hiding what happens specifically on its errors. See
confidence-at-errors below for the number that actually matters for a
fallback-queue design.

### Confidence at errors

Restricted to CT5 (arithmetic), where nearly all errors of both arms live:

| Arm | Confidence at errors | Confidence at correct | Gap |
|---|---|---|---|
| Jev | 0.433 (n=67) | 0.911 (n=653) | **0.478** |
| Haiku | 0.986 (n=131) | 0.987 (n=589) | **0.001** |

**Jev's confidence is a decision-usable signal for a fallback/review
queue; Haiku's is not.** A rule like "route anything under 0.6 confidence
to human review" would catch the large majority of Jev's arithmetic
mistakes. Haiku's confidence is statistically indistinguishable between
its errors and its correct predictions on the identical task — it fails
confidently, with nothing for a downstream system to act on. This is the
single most decision-relevant number in this benchmark for a firm planning
to keep a fallback path, per test-plan.md §6's framing.

### Run-to-run variance (both arms, full 3 repeats, all 8 clause types)

| Arm | CT1-4 disagreement | CT5-8 disagreement |
|---|---|---|
| Jev | 0/2,880 (0.00%) | 5/1,920 (0.26%) |
| Haiku | — | 28/1,920 (1.46%) |

Jev is meaningfully more repeat-to-repeat stable than Haiku throughout.

### Latency and cost per document

Jev: 5,764 total calls across all 8 clause types, $0.1809 total (separate
provider, never touches the Anthropic budget). Haiku: 5,774 total calls,
$9.1786 total. Full breakdown in `results/spend_ledger.jsonl` /
`python -m harness.spend_ledger`.

### Sonnet 5 comparison (added later — see methodology.md §16)

A Sonnet 5 comparison was proposed early on (per prior instruction,
triggered by Haiku underperforming Jev), explicitly declined at the time
("if jev did 100%, not worth testing the other stuff"), then revisited
once CT9/CT10 existed and showed Haiku underperforming Jev by a wider
margin than CT1-8 ever did. Full scope built and run: same rubric, same
forced tool-use, same 3-repeat × 4-condition grid as Haiku.

**Accuracy per (condition × clause type) — CT1-4, Sonnet at full 3 repeats:**

| Clause type | sonnet A | sonnet B | sonnet C | sonnet SHUFFLE |
|---|---|---|---|---|
| CT1 descriptive | 1.00 | 1.00 | 1.00 | 1.00 |
| CT2 conjunctive+threshold | 1.00 | 1.00 | 1.00 | 1.00 |
| CT3 relational | 1.00 | 1.00 | 0.98 | 1.00 |
| CT4 negative/exclusionary | 1.00 | 1.00 | 1.00 | 1.00 |

CT1-4 overall: **99.90%** (2,877/2,880) — essentially tied with Jev's
100.00%, and meaningfully ahead of Haiku's 97.74%. Sonnet's only CT1-4
errors are 3 CT3 relational-lookup slips under Condition C.

**Accuracy per (condition × clause type) — CT5-8 "hard mode," Sonnet at full 3 repeats:**

| Clause type | sonnet A | sonnet B | sonnet C | sonnet SHUFFLE |
|---|---|---|---|---|
| CT5 computed_threshold (arithmetic) | 0.86 | 0.90 | 0.83 | 0.86 |
| CT6 temporal_reasoning (dates) | 1.00 | 1.00 | 1.00 | 1.00 |
| CT7 multi_hop_relational | 1.00 | 1.00 | **0.34** | 1.00 |
| CT8 long_context_distractor | 1.00 | 1.00 | 1.00 | 1.00 |

CT5-8 overall: **92.47%** (2,663/2,880) — the *worst* of the three models
on hard mode, driven almost entirely by one isolated cell: **CT7 under
Condition C collapses to 34.4% (62/180)**, a 65.6-point drop from every
other CT7 cell (all 100.00%, matching both Jev and Haiku exactly). This is
a genuinely new finding relative to the CT1-4-only Haiku comparison — CT7
(multi-hop lookup) was originally hypothesized to be hard for Jev
specifically and never materialized as a weakness for Jev *or* Haiku; it
turns out to be Sonnet's single sharpest failure in the entire CT1-8
suite, and neither of the other two models share it at all.

Mechanism (consistent with a label-collision hypothesis, same shape as
OpenJev's independent CT7-C collapse in Part 3): errors are high-confidence
(mean 0.947, essentially identical to the 0.941 mean at correct
predictions on the same cell — confidently wrong, not uncertain) and not
consistently biased toward one wrong folder (repeat-to-repeat, the same
document sometimes lands on different incorrect folders), suggesting a
genuine two-hop-lookup failure under misleading-but-plausible folder names
rather than a single fixed prior. CT5 arithmetic error rate is 13.7%
(vs. Jev 9.3%, Haiku 18.2% — better than Haiku, worse than Jev). CT6 and
CT8 are clean 100.00% for Sonnet, same as both other models.

**Calibration**: raw ECE 0.0141, fitted temperature 1.00 (no improvement,
same as Haiku) — Sonnet's confidence is not calibrated as computed. CT5
confidence-at-errors 0.970 (n=99) vs. confidence-at-correct 0.979 (n=621),
gap **0.0097** — essentially flat, the same "fails confidently" pattern as
Haiku (gap 0.001), nowhere near Jev's 0.478 gap.

**Run-to-run variance**: 25/1,920 (1.30%) — between Jev (0.26%) and Haiku
(1.46%), not the most nor the least stable of the three.

**Price**: 5,760 calls, $20.7320 total — 2.26x Haiku's per-call rate on
this task (slightly above the pricing table's flat 2.00x multiplier,
consistent with Sonnet's real prompts/outputs running marginally larger
than Haiku's, not just costing more per token).

## Comparison summary (per test-plan.md §6, "Comparison framework for Part 2")

**Jev >= both Claude models on accuracy**, on both the original corpus
(100.00% vs Haiku 97.74%, Sonnet 99.90%) and a corpus specifically
designed to find Jev's limits (97.67% vs Haiku 95.17%, Sonnet 92.47% —
Sonnet is the *worst* of the three here). Jev has exactly one real
weakness (arithmetic near a stated threshold) — predicted in advance by
the vendor's own jaggedness documentation — but fails on it *less* than
either Claude model (9.3% vs Haiku's 18.2%, Sonnet's 13.7% error rate on
CT5), and its confidence degrades sharply and usefully on precisely the
cases it gets wrong, unlike either Claude model's. Two other a priori
plausible weaknesses (multi-hop indirection, long-context distraction)
did not materialize for Jev or Haiku, but multi-hop indirection (CT7) did
materialize for Sonnet specifically, collapsing to 34.4% under Condition
C alone — the strongest model tested has the single sharpest, most
isolated failure mode in this whole suite, discovered only because the
comparison was widened rather than stopped after Haiku.

A Sonnet 5 comparison was proposed early on (per prior instruction,
triggered by Haiku underperforming Jev) and initially declined by the
user: "if jev did 100%, not worth testing the other stuff. that's
insanely good." It was revisited later, after CT9/CT10 showed Haiku
underperforming Jev by a wider margin than CT1-8 ever did, and built at
full scope across all three task families (methodology.md §16). Anthropic
spend for the full benchmark (corpus generation + Haiku + Sonnet):
$109.36 of a $110.00 budget, raised in stages from an original $5.00,
each raise with explicit user approval and a prior cost projection (see
methodology.md §12, §13, §15, §16).

## Part 3 — OpenJev fallback viability

`CODIV_API_KEY` became available; OpenJev run at full scope on both CT1-8
and CT9, matching Jev's own scope exactly. $0 real cost (free Codiv
tier); estimated self-hosted cost (methodology.md §17, added later) is
~$0.08 (CT1-8) and ~$0.20 (CT9) -- still far below every metered API arm.
Full mechanism writeup: [methodology.md §14](./methodology.md#14-openjev-the-fallback-viability-arm-test-plan.mds-part-3).

### CT1-8 accuracy

**Overall: 96.28%** (5,546/5,760, 95% CI [0.958, 0.968]).

| Clause type | A | B | C | SHUFFLE |
|---|---|---|---|---|
| CT1 descriptive | 0.99 | 1.00 | 1.00 | 0.94 |
| CT2 conjunctive_threshold | 1.00 | 1.00 | 1.00 | 1.00 |
| CT3 relational | 0.97 | 0.96 | 0.95 | 0.98 |
| CT4 negative_exclusionary | 1.00 | 1.00 | 1.00 | 1.00 |
| CT5 computed_threshold | 0.92 | 0.89 | 0.92 | 0.92 |
| CT6 temporal_reasoning | 1.00 | 1.00 | 1.00 | 0.98 |
| CT7 multi_hop_relational | 1.00 | 1.00 | **0.40** | 1.00 |
| CT8 long_context_distractor | 1.00 | 0.99 | 1.00 | 1.00 |

**CT5's arithmetic weakness replicates for a third and fourth model**
(OpenJev 65/720 errors, Sonnet 99/720 — see Part 2's Sonnet section),
100% within the near-threshold band, reinforcing this as a genuine,
convergent limitation rather than an implementation quirk of any one
model. **CT7 Condition C collapses to 40%** — traced to a clean,
deterministic mechanism: OpenJev's two-hop team→division→program lookup
misroutes DIV-A's teams to DIV-B's correct answer 100% of the time, while
DIV-B is never wrong and DIV-C is mostly wrong. Critically, the *identical*
tree scores 100% under SHUFFLE (opaque random-id relabeling) — so this
isn't "adversarial relabeling defeats OpenJev" in general, it's
specifically that Condition C's relabeling uses *other real, equally
plausible* program names, creating label-collision risk that opaque ids
don't. **Sonnet collapses on the exact same cell, independently, to a
similar 34.4%** (Part 2) — two structurally unrelated models hitting the
same specific trap, while Jev and Haiku both score 100% on it. That
makes CT7-under-Condition-C the single clearest quality gap in this
benchmark that splits 2-and-2 rather than isolating one arm.

### Calibration & stability

Confidence at errors (0.396) vs. correct (0.901) — a 0.505 gap, comparable
to Jev's own discrimination and far better than Haiku's near-zero gap.
Disagreement: 16/1,920 = 0.83% (between Jev's 0.26% and Haiku's 1.46%).

### CT9 (chained decision-tree execution)

| k | jev | haiku | sonnet | openjev |
|---|---|---|---|---|
| 1 | 0.750 | 0.578 | **0.867** | 0.428 |
| 2 | 0.711 | 0.533 | 0.578 | 0.256 |
| 5 | 0.311 | 0.317 | 0.300 | 0.194 |
| 10 (semantic) | 0.294 | 0.317 | 0.228 | 0.156 |
| 10 (opaque) | 0.339 | 0.317 | 0.228 | 0.206 |

Same qualitative pattern for every arm (smaller steps win decisively), but
OpenJev sits below all three others at every k and degrades faster.
Sonnet is the outlier: **best of all four at k=1** (+11.7pp over Jev,
+28.9pp over Haiku, +43.9pp over OpenJev), then crosses below Jev by k=2
and ends **worst of all four at k=10** (0.228, below even OpenJev's
0.206/0.156). Disagreement at k=10: OpenJev 13.3% (semantic) / 1.7%
(opaque); Sonnet 3.3% (semantic) / **20.0%** (opaque) — the single highest
disagreement rate in this benchmark. Neither the "least stable" label nor
the accuracy ranking is fixed to one arm once Sonnet is in the comparison.

### Verdict

**Viable, low-cost fallback for CT1-8-style rubric classification** (96.28%
overall, one specific, routable gap at CT7/misleading conditions, shared
with Sonnet; $0.00 real cost here, ~$0.014/1,000 calls if self-hosted for
real — methodology.md §17). **Not currently viable for CT9-style chained
execution** — meaningfully behind Jev and Haiku at low-to-mid k, with
faster degradation and (on semantic labeling) worse run-to-run stability
than either — though no longer uniquely so: Sonnet's k=10/opaque
instability (20.0%) is worse than OpenJev shows anywhere. A firm using
Jev as primary could reasonably scope an OpenJev fallback to single-hop
classification tasks, not long decision chains.

## Part 5 — CT10: AP World History exam grading

A third structurally distinct test: partial-credit rubric grading of
open-ended paragraph answers (not classification), across 100 students,
30 questions, a realistic non-uniform rubric summing to 100 points,
**chained** (one call/question) vs. **whole-exam** (one call, all 30)
grading modes, and **with-answer-key vs. without** (testing whether a
model needs the key or already knows the material). Originally 3 arms
(Jev, Haiku, OpenJev), full scope, `repeats=1`; Sonnet added later at the
same scope (methodology.md §16). Full design and mechanism analysis:
[methodology.md §15](./methodology.md#15-ct10-ap-world-history-exam-grading).

### Per-question grading accuracy (exact-match rate, 3,000 gradings/cell)

| Arm | Mode | Without key | With key |
|---|---|---|---|
| Jev | chained | 0.80 | 0.87 |
| Jev | whole_exam | 0.83 | 0.88 |
| Haiku | chained | 0.83 | 0.86 |
| Haiku | whole_exam | 0.68 | 0.71 |
| Sonnet | chained | 0.83 | **0.96** |
| Sonnet | whole_exam | **0.47** | 0.60 |
| OpenJev | chained | 0.73 | 0.79 |
| OpenJev | whole_exam | 0.58 | 0.57 |

**Does the model need the answer key, or does it know the material?**
All four benefit from the key, but by very different margins: Jev +0.048
to +0.070, Haiku +0.025 to +0.030 (smallest of the three original arms —
Haiku's own AP World History knowledge is doing almost as much work as
the literal key), OpenJev +0.060 (chained) but ~0 (whole-exam, likely a
floor effect), **Sonnet +0.13 (chained) — the single largest with/without-key
gap of any arm** — Sonnet leans on the key harder than any other model
tested, and delivers its single best result in this entire benchmark
family when it has one (chained + with_key: 0.9613 exact-match, MAE
0.039, beating every other arm/mode/key combination).

**Does bulk-grading architecture matter?** Decisively yes, and Sonnet is
the most extreme case, not an exception. Jev is essentially flat between
chained and whole-exam (-0.004 to -0.025, whole-exam even marginally
*better*). Haiku and OpenJev both drop 15-22 percentage points in
whole-exam mode. **Sonnet drops 36 points** (chained-with-key 0.96 →
whole-exam-with-key 0.60; without-key 0.83 → 0.47) — more than double
Haiku's or OpenJev's degradation, and the model that was *best* of the
four in chained mode becomes *worst* of the four in whole-exam mode.
Total-exam-score MAE tells the same story more starkly: Sonnet
whole-exam-without-key total-score error is **16.44 points** (100-point
exam) vs. Jev's 4.63 and Haiku's 8.84 — roughly 3.6x Jev's error and 1.9x
Haiku's, on the exact same students and rubric. Mechanism: Jev's
`system_one` call natively evaluates multiple `Score` questions in
parallel within one round-trip, so its "whole exam" call is
architecturally ~30 independent judgments, not one bulk task. Haiku,
Sonnet, and OpenJev have no such primitive — whole-exam mode forces a
single shared JSON object holding all 30 scores at once, a genuinely
harder task shape for all three, and evidently a much harder one for
Sonnet specifically than for either of the other two. This is *avoidable
by architecture*, not an inherent model-quality gap — but it is a real,
sharp capability cliff for Sonnet that a chained-mode-only evaluation
would have completely missed.

### Calibration (chained mode — the only mode with per-question confidence for all arms)

| Arm | Confidence at errors | Confidence at correct | Gap |
|---|---|---|---|
| Jev | 0.754 | 0.915 | **0.161** |
| Haiku | 0.887 | 0.902 | **0.015** |
| Sonnet | 0.839 | 0.909 | **0.070** |
| OpenJev | 0.766 | 0.873 | **0.107** |

Same ranking pattern as CT5 and CT9 — Jev's confidence discriminates
correctness most sharply. Sonnet's gap (0.070) is larger than Haiku's
(0.015) but still far below Jev's (0.161) or OpenJev's (0.107) — its
confidence is somewhat more informative than Haiku's here, but nowhere
near a substitute for Jev's, and this calibration number says nothing
about the much larger whole-exam-mode collapse above (whole-exam has no
per-question confidence field to compare).

### Cost

Jev $0.25, Haiku $10.22, Sonnet $22.82, OpenJev $0.00 real / ~$0.15
self-hosted estimate (12,000 grade rows/arm; Sonnet 2.23x Haiku's rate on
this task; OpenJev's self-hosted estimate added later, methodology.md
§17). Cumulative Anthropic
spend at the end of the original 3-arm CT10 phase: **$41.26 / $50.00**,
$8.74 remaining. Final cumulative spend after adding Sonnet across all
three task families: **$109.36 / $110.00**, $0.64 remaining
(methodology.md §16).

## Part 4 — CT9: can either model chain a long sequence of decisions?

A structurally different test from CT1-8 (single document → single
folder): a 10-layer decision tree over a 30-question compliance
questionnaire, walked in chunks of size k ∈ {1,2,5,10}, with **real
compounding** between chunks (each chunk starts wherever the model's own
previous answer landed, never rescued to ground truth). Full design and
mechanism analysis: [methodology.md §13](./methodology.md#13-ct9-chained-decision-tree-execution).

### End-to-end accuracy by k

| k | jev | haiku | sonnet |
|---|---|---|---|
| 1 (10 handoffs) | 0.750 | 0.578 | **0.867** |
| 2 (5 handoffs) | **0.711** | 0.533 | 0.578 |
| 5 (2 handoffs) | 0.311 | **0.317** | 0.300 |
| 10 (single shot, semantic labels) | 0.294 | **0.317** | 0.228 |
| 10 (single shot, opaque labels) | 0.339 | 0.317 | 0.228 |

**Headline finding: accuracy degrades as k increases** — every model does
far better with frequent small handoffs than with one unassisted
full-chain trace, the opposite of the a priori "more handoffs = more
compounding risk = worse" hypothesis. Jev's advantage over Haiku is
concentrated at small step sizes (+17-18pp at k=1/2) and disappears
entirely at k=5/10, where the two are statistically tied. **Sonnet
crosses both other lines, in opposite directions.** At k=1 it's the best
of the three by a wide margin (+11.7pp over Jev, +28.9pp over Haiku) —
the strongest single-step reasoner wins decisively when there's only one
step to reason about. By k=10 it's the *worst* of the three (0.228 vs.
Jev's 0.294-0.339 and Haiku's 0.317) — added capability did not translate
into holding up over one large, unassisted, multi-step call; the crossover
happens between k=2 and k=5, where all three converge to within a few
points of each other. The semantic-vs-opaque check at k=10 (designed to
catch "vibe"-based shortcutting) found none for any of the three models —
opaque labels performed the same or better, never worse, ruling out
shortcut-guessing as the explanation for the low k=10 numbers.

### Calibration (confidence at locally-correct vs. locally-incorrect chunks)

| Arm | Confidence, local errors | Confidence, local correct | Gap |
|---|---|---|---|
| Jev | 0.400 (n=575) | 0.885 (n=2,845) | **0.485** |
| Haiku | 0.928 (n=740) | 0.976 (n=2,680) | **0.048** |
| Sonnet | 0.941 (n=601) | 0.980 (n=2,819) | **0.039** |

Replicates CT5's calibration finding (Part 2) on a completely unrelated
task: Jev's confidence is a real, usable signal for flagging likely-wrong
steps mid-chain; both Claude models' stay high almost regardless of
correctness, Sonnet's gap even slightly smaller than Haiku's.

### Run-to-run disagreement at k=10 — the one place Jev is less stable than Haiku, but not than Sonnet

Jev: 5/60 forms (8.3%) gave a different final answer across 3 repeats
(6/60 = 10% under opaque labeling specifically). Haiku: 0/60 (0%), both
labelings. This is a genuine reversal of every CT1-8 disagreement finding
(where Jev was consistently more stable) — reported as found, since k=10
single-shot full-tree tracing is also Jev's single worst accuracy result
anywhere in this benchmark (29.4%), and instability under genuine
difficulty is exactly what you'd expect to eventually surface once a
benchmark pushes hard enough to find it. **Sonnet is less stable still,
but only under opaque labeling**: 2/60 (3.3%) semantic vs. **12/60 (20.0%)**
opaque — the single highest disagreement rate found anywhere in this
project, more than double Jev's worst figure and with no equivalent for
Haiku at all.

### Cost

Jev: 3,420 calls, $0.3192 (negligible, separate provider). Haiku: 3,420
calls, $10.2672. Sonnet: 3,420 calls, $24.5497 (2.39x Haiku's rate on this
task — a real prompt/output-size effect on top of the flat 2.00x pricing
multiplier, since chunk descriptions grow with k and both compound).
Combined with all prior phases, final Anthropic spend:
**$24.11 / $30.00** budget (raised from an original $5.00 across two prior
approvals plus this one, each with an explicit prior cost projection).
