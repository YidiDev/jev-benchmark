# Results — Rubric-Based Zero-Shot Classification Model Benchmark

Living document. Filled in as runs complete. See [`methodology.md`](./methodology.md)
for how these numbers were produced and [`test-plan.md`](./test-plan.md) for
the design these results answer.

Status: **Corpus complete (240 docs). Local baseline arms (nli-bart, emb-bge)
and the Jev arm have produced raw predictions across the full corpus**,
including the shuffle control — see
[`methodology.md` §9](./methodology.md#9-local-baseline-arms-phase-2-actual)
and [§10](./methodology.md#10-jev-arm-phase-3-actual) for un-scored
sanity-check numbers. Formal accuracy tables with bootstrap CIs below await
the scoring harness (Phase 6) and the Haiku/OpenJev arms.

---

## Part 1 — Does Jev condition on the rubric? (vs NLI)

**Preliminary answer: yes, unambiguously.** Raw (non-bootstrapped) accuracy
over the full 240-doc corpus × 3 repeats; formal CIs land in Phase 6.

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

**Preliminary answer: no, Jev beats Haiku on this corpus.** Jev: 100.00%
(2,880/2,880). Haiku: 97.66% (1,875/1,920). Raw accuracy, pre-bootstrap-CI
(formal CIs land in Phase 6); Haiku ran at 2 repeats instead of 3 for
budget reasons, see methodology.md §11.

### Accuracy per (condition × clause type) — raw, pre-bootstrap

| Clause type | jev A | jev B | jev C | jev SHUFFLE | haiku A | haiku B | haiku C | haiku SHUFFLE |
|---|---|---|---|---|---|---|---|---|
| CT1 descriptive | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.97 | 1.00 |
| CT2 conjunctive+threshold | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 | 1.00 |
| CT3 relational | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 0.93 | 0.93 | 0.92 |
| CT4 negative/exclusionary | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.98 | 1.00 |

**82% of Haiku's errors (37/45) are CT3 relational-lookup failures with a
single, consistent mechanism**: confusing a non-retainer distractor client
name for a real retainer-list client because they share a prefix word (e.g.
"Anchor Robotics" → wrongly treated as retainer "Anchor Materials"), at high
confidence (0.95–1.00). Jev resolves the identical documents correctly
(manually spot-checked). This is exactly the clause type test-plan.md §3
predicted would be hardest -- it just turned out to be hard for Haiku, not
for Jev, on this corpus. See methodology.md §11 for the full breakdown.

### Calibration (ECE, raw and temperature-fit)

*(pending — Phase 6)*

### Confidence at errors

Haiku's 45 misclassifications carry confidence 0.95–1.00 in every checked
case (i.e. confidently wrong, not hedged) -- a real calibration concern to
quantify formally in Phase 6.

### Run-to-run variance (repeats: jev=3, haiku=2 — see methodology.md §11 for why Haiku is 2)

Haiku repeat-1-vs-repeat-2 disagreement: 7/960 = 0.73% (small but nonzero,
confirming non-determinism persists with no temperature parameter exposed
by this API). Jev 3-repeat disagreement: 0/2,880 — perfectly consistent
across all 3 repeats in this run (ties directly to the 100% ceiling
accuracy: a run with zero errors has zero opportunity to disagree with
itself).

### Latency and cost per document

Jev: 2,880 calls, well under $0.10 total, output free. Haiku: 1,920
production calls (1,934 incl. smoke tests), $2.8804. Full breakdown in
`results/spend_ledger.jsonl` / `python -m harness.spend_ledger`.

## Decision (per test-plan.md §6, "Decision rule for Part 2")

**Jev >= Haiku on accuracy → adopt.** Jev 100.00% vs Haiku 97.66% on the
identical corpus, conditions, and rubric decomposition. A Sonnet 5
comparison was proposed (per prior instruction, triggered by Haiku
underperforming Jev) and explicitly declined by the user given how decisive
this result already is: "if jev did 100%, not worth testing the other
stuff. that's insanely good." No Sonnet arm was built; $1.06 of the $5.00
Anthropic budget remains unspent. Formal bootstrap CIs (Phase 6) and the
full pilot→3-repeat run structure (Phases 7-8) still apply to firm up this
number, but the qualitative conclusion is not expected to change: Jev's
errors were zero across 2,880 predictions spanning every clause type,
condition, and the shuffle control, while Haiku's 45 errors were
concentrated in one well-understood clause type (CT3 relational lookup).

## Part 3 — OpenJev fallback viability

*(pending — lower priority, built once CODIV_API_KEY is available)*
