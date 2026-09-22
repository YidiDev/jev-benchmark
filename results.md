# Results — Rubric-Based Zero-Shot Classification Model Benchmark

Living document. Filled in as runs complete. See [`methodology.md`](./methodology.md)
for how these numbers were produced and [`test-plan.md`](./test-plan.md) for
the design these results answer.

Status: **Corpus complete (240 docs). Local baseline arms (nli-bart, emb-bge)
have produced raw predictions across the full corpus** — see
[`methodology.md` §9](./methodology.md#9-local-baseline-arms-phase-2-actual)
for un-scored sanity-check numbers. Formal accuracy tables with bootstrap CIs
below await the scoring harness (Phase 6) and the Jev/Haiku/OpenJev arms.

---

## Part 1 — Does Jev condition on the rubric? (vs NLI)

*(pending)*

### Accuracy per (condition × clause type)

*(pending — table with bootstrap 95% CIs)*

### Shuffle-control delta

*(pending)*

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
