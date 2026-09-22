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

## Part 2 — Does Jev match Haiku 4.5 on quality? (the adoption decision)

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

## Decision (per test-plan.md §6, "Decision rule for Part 2")

**Jev >= Haiku on accuracy → adopt.** True on both the original corpus
(100.00% vs 97.74%) and a corpus specifically designed to find Jev's
limits (97.67% vs 95.17% on CT5-8). Jev has exactly one real weakness
(arithmetic near a stated threshold) — predicted in advance by the
vendor's own jaggedness documentation — but fails on it *less* than the
reference-ceiling LLM (9.3% vs 18.2% error rate on CT5), and its
confidence degrades sharply and usefully on precisely the cases it gets
wrong, unlike Haiku's. Two other a priori plausible weaknesses (multi-hop
indirection, long-context distraction) did not materialize for either
model at the scale tested. A Sonnet 5 comparison was proposed early on
(per prior instruction, triggered by Haiku underperforming Jev) and
explicitly declined by the user: "if jev did 100%, not worth testing the
other stuff. that's insanely good." No Sonnet arm was built. Anthropic
spend: $12.03 of a $12.50 budget (raised twice from an original $5.00,
both times with explicit user approval and a prior cost projection — see
methodology.md §12).

## Part 3 — OpenJev fallback viability

`CODIV_API_KEY` became available; OpenJev run at full scope on both CT1-8
and CT9, matching Jev's own scope exactly. $0 cost (free Codiv tier).
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

**CT5's arithmetic weakness replicates for a third model** (65/720
errors, 100% within the near-threshold band), reinforcing this as a
genuine, convergent limitation rather than an implementation quirk of any
one model. **CT7 Condition C collapses to 40%** — traced to a clean,
deterministic mechanism: OpenJev's two-hop team→division→program lookup
misroutes DIV-A's teams to DIV-B's correct answer 100% of the time, while
DIV-B is never wrong and DIV-C is mostly wrong. Critically, the *identical*
tree scores 100% under SHUFFLE (opaque random-id relabeling) — so this
isn't "adversarial relabeling defeats OpenJev" in general, it's
specifically that Condition C's relabeling uses *other real, equally
plausible* program names, creating label-collision risk that opaque ids
don't. Jev and Haiku both score 100% on this exact cell — the single
clearest quality gap found between OpenJev and the other two arms in this
entire benchmark.

### Calibration & stability

Confidence at errors (0.396) vs. correct (0.901) — a 0.505 gap, comparable
to Jev's own discrimination and far better than Haiku's near-zero gap.
Disagreement: 16/1,920 = 0.83% (between Jev's 0.26% and Haiku's 1.46%).

### CT9 (chained decision-tree execution)

| k | jev | haiku | openjev |
|---|---|---|---|
| 1 | 0.750 | 0.578 | 0.428 |
| 2 | 0.711 | 0.533 | 0.256 |
| 5 | 0.311 | 0.317 | 0.194 |
| 10 (semantic) | 0.294 | 0.317 | 0.156 |
| 10 (opaque) | 0.339 | 0.317 | 0.206 |

Same qualitative pattern as Jev/Haiku (smaller steps win decisively), but
OpenJev sits below both at every k and degrades faster. Disagreement at
k=10: 13.3% — the least stable of the three arms on this benchmark's
hardest single task.

### Verdict

**Viable, free fallback for CT1-8-style rubric classification** (96.28%
overall, one specific, routable gap at CT7/misleading conditions).
**Not currently viable for CT9-style chained execution** — meaningfully
behind both other arms at every chunk size, with faster degradation and
the worst run-to-run stability. A firm using Jev as primary could
reasonably scope a zero-cost OpenJev fallback to single-hop classification
tasks, not long decision chains.

## Part 4 — CT9: can either model chain a long sequence of decisions?

A structurally different test from CT1-8 (single document → single
folder): a 10-layer decision tree over a 30-question compliance
questionnaire, walked in chunks of size k ∈ {1,2,5,10}, with **real
compounding** between chunks (each chunk starts wherever the model's own
previous answer landed, never rescued to ground truth). Full design and
mechanism analysis: [methodology.md §13](./methodology.md#13-ct9-chained-decision-tree-execution).

### End-to-end accuracy by k

| k | jev | haiku |
|---|---|---|
| 1 (10 handoffs) | **0.750** | 0.578 |
| 2 (5 handoffs) | **0.711** | 0.533 |
| 5 (2 handoffs) | 0.311 | 0.317 |
| 10 (single shot, semantic labels) | 0.294 | 0.317 |
| 10 (single shot, opaque labels) | 0.339 | 0.317 |

**Headline finding: accuracy degrades as k increases** — both models do
far better with frequent small handoffs than with one unassisted
full-chain trace, the opposite of the a priori "more handoffs = more
compounding risk = worse" hypothesis. Jev's advantage over Haiku is
concentrated at small step sizes (+17-18pp at k=1/2) and disappears
entirely at k=5/10, where the two are statistically tied. The
semantic-vs-opaque check at k=10 (designed to catch "vibe"-based
shortcutting) found none for either model — opaque labels performed the
same or better, never worse, ruling out shortcut-guessing as the
explanation for the low k=10 numbers.

### Calibration (confidence at locally-correct vs. locally-incorrect chunks)

| Arm | Confidence, local errors | Confidence, local correct | Gap |
|---|---|---|---|
| Jev | 0.400 (n=575) | 0.885 (n=2,845) | **0.485** |
| Haiku | 0.928 (n=740) | 0.976 (n=2,680) | **0.048** |

Replicates CT5's calibration finding (Part 2) on a completely unrelated
task: Jev's confidence is a real, usable signal for flagging likely-wrong
steps mid-chain; Haiku's stays high almost regardless of correctness.

### Run-to-run disagreement at k=10 — the one place Jev is less stable

Jev: 5/60 forms (8.3%) gave a different final answer across 3 repeats.
Haiku: 0/60 (0%). This is a genuine reversal of every CT1-8 disagreement
finding (where Jev was consistently more stable) — reported as found,
since k=10 single-shot full-tree tracing is also Jev's single worst
accuracy result anywhere in this benchmark (29.4%), and instability under
genuine difficulty is exactly what you'd expect to eventually surface once
a benchmark pushes hard enough to find it.

### Cost

Jev: 3,420 calls, $0.3192 (negligible, separate provider). Haiku: 3,420
calls, $10.2672. Combined with all prior phases, final Anthropic spend:
**$24.11 / $30.00** budget (raised from an original $5.00 across two prior
approvals plus this one, each with an explicit prior cost projection).
