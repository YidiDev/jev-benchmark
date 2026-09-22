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

*(pending)*

### Accuracy per (condition × clause type)

*(pending)*

### Calibration (ECE, raw and temperature-fit)

*(pending)*

### Confidence at errors

*(pending)*

### Run-to-run variance (3 repeats)

*(pending)*

### Latency and cost per document

*(pending — actual logged spend, not list price)*

## Decision (per test-plan.md §6, "Decision rule for Part 2")

*(pending — not to be filled in until the full run completes)*

## Part 3 — OpenJev fallback viability

*(pending — lower priority, built once CODIV_API_KEY is available)*
