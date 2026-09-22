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

*(pending — lower priority, built once CODIV_API_KEY is available)*
