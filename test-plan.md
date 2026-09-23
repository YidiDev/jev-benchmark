# Jev Rubric-Conditioning Test

**Question:** Does Jev evaluate a multi-clause rubric over file content, in a way that NLI-based zero-shot classification structurally cannot?

**Claim being tested:** Jev is not a zero-shot classifier with better marketing. It conditions on instructions; NLI conditions on label-text similarity.

**Second question (Part 2):** Does Jev match a cheap LLM on the same rubric-based assessment? Haiku 4.5 is the floor. If Jev loses to Haiku on quality, there is no reason to evaluate more expensive models — the LLM path was already affordable for this workload.

Part 1 (vs NLI) is an existence proof. Part 2 (vs Haiku) is the harder comparison — it measures whether Jev's rubric-conditioning holds up against a capable general-purpose model, not just against a non-contender.


Status: design only, not yet run. Drafted 2026-09-21.

---

## 1. Task

Sort documents into a directory structure. Each folder has a destination rule; the model sees file content plus the rule set and picks the folder.

This task was chosen because **ground truth is free**. The corpus is constructed with known-correct assignments, so there is no labeling bottleneck — the constraint that makes most classifier evaluations expensive. One person can run this end to end.


---

## 2. Conditions

Three folder-naming conditions over the same corpus and the same rubric:

| Condition | Folder names | What it isolates |
|---|---|---|
| **A. Semantic** | `invoices/`, `contracts/`, `tax/` | Baseline. Label semantics and rubric agree. |
| **B. Opaque** | `k2m8p1/`, `x7f3q9/`, `b4n0z2/` | Removes label semantics entirely. NLI has nothing to score against. |

| **C. Misleading** | Folder named `invoices/` whose rubric clause says receipts go there | Does the model follow the rubric *over* the label prior when they conflict? |

Condition C matters more than it looks. B confounds two variables — removing label semantics *and* adding an indirection hop from clause to folder ID. C isolates rubric-following cleanly, and it is the condition where Jev might genuinely fail.

---

## 3. Clause complexity gradient

Run each clause type as a separate scored bucket. Do not pool them. "Jev holds from descriptive through relational while NLI is at chance from the start" is a far stronger finding than one aggregate number, and it tells you where the ceiling is.

| Type | Example | NLI expectation (Condition A) |
|---|---|---|
| **1. Descriptive** | "Tax documents go to A." | Handles fine — this is a valid hypothesis. |
| **2. Conjunctive + threshold** | "Invoices over $10k to A, under to B." | Breaks. Entailment over one hypothesis cannot evaluate a numeric condition. |

| **3. Relational** | "Goes wherever its parent project goes." / "Anything naming a client on the retainer list goes to C." | Hard break. No single-hypothesis formulation exists. |
| **4. Negative / exclusionary** | "Contracts, unless superseded — then archive." | Breaks. Negation is a known NLI weak point. |

Minimum ~50 documents per clause type per condition, stratified across folders.


---

## 4. Arms

| Arm | Implementation | Role |
|---|---|---|
| `jev` | `typesafe/jev-1.13.x`, one `choice` question per document, rubric in the state | Subject |
| `nli-bart` | `facebook/bart-large-mnli`, HF zero-shot pipeline, hypothesis `This document belongs in {folder}` | Instrument |
| `emb-bge` | `BAAI/bge-m3`, cosine to folder description | Stronger traditional baseline |

| `haiku` | `claude-haiku-4-5`, temp 0, same rubric, constrained JSON output (`{folder_id, confidence}`) | **Reference ceiling — the comparison arm for Part 2** |
| `openjev` | `razorback16/openjev` (DiffusionGemma 26B-A4B, Apache-2.0, vLLM) — speaks Jev's wire API, so the SDK works unchanged | **Fallback path — is the open version good enough?** |

**Note on the NLI arm.** It is here as an instrument, not a competitor. It is *expected* to fail on Conditions B and C — that failure is the finding, not a flaw in the setup. This is an ablation demonstrating a structural capability gap, not a fair fight. Do not steelman it by moving rubric clauses into the hypothesis slot; that defeats the purpose of the design.

`emb-bge` is included because it beat NLI decisively on high-cardinality classification in the published benchmark (.722 vs .579 on Banking77). If you only beat NLI, you beat the weaker opponent.


**Note on the Haiku arm.** This one *is* a fair fight and must be run as one. Same rubric text, same decomposition, same folder set, temperature 0, 3 repeats to measure non-determinism. Give the Haiku prompt the same number of tuning passes as the Jev rubric, on the validation split. The published LiteLLM comparison is a useful reference point (126.81ms median for Jev vs 688.40ms for Haiku, 5.43x) but it measured label agreement on routing, not multi-clause rubric depth — so it does not answer this.

Expect the LLM to win on **clause type 3 (relational)**, where multi-hop reasoning over a retainer list or parent-project lookup is exactly what autoregressive generation is good at and a single forward pass is not. If Jev holds on types 1, 2 and 4 and loses only on 3, that is a useful and honest boundary, not a failure.


**Note on the openjev arm.** "openjev" is not one project and is not an official open Jev — TypeSafe has released neither weights nor training method. It is a collective term for independent reimplementations of the interface pattern on frozen open models. The authors are explicit that what was reproduced is the I/O types, not the model or its training.

The mechanism differs from Jev's in a way that matters here: these read the probability of each option straight off the next-token distribution of a frozen open model in one forward pass, with nothing generated and nothing parsed. That yields typed outputs and speed but **not** RLCD-style calibration training.


Arm selection:
- **Primary: `razorback16/openjev`** — DiffusionGemma 26B-A4B (Apache-2.0) on vLLM, Docker image available, ~18 GB weights, and critically it speaks the same wire API as Jev so the same client code drives both arms. Cheapest possible swap.
- Reference implementation for the idea itself is `TheoLeeCJ/SemIf` (originally released as OpenJev) — more careful eval harness, perturbation tests, reranker comparison. Worth reading even if not run.
- `Meanblock/JEV-CPU` (Qwen3-0.6B, CPU-only, ~1s decisions) is a useful low-end datapoint if you want to know how far down the model-size curve this still works. Optional.


The openjev arm answers the question that actually governs client architecture: **is there a fallback if TypeSafe's pricing moves or the waitlist closes?**

---

## 5. Controls

### 5.1 Shuffle control (required)


**The failure mode of this design is not NLI doing badly — it is being unable to distinguish "Jev read the rubric" from "Jev pattern-matched the file to a plausible folder and got lucky."**

Run the identical corpus and identical opaque folder IDs with **rubric clauses permuted across folder IDs**.

- If Jev is genuinely conditioning: accuracy tracks the *permuted* assignment. It should confidently sort into the semantically "wrong" folder, following the rubric off a cliff.
- If Jev still lands on the semantically sensible folder: it is ignoring the rubric and using content priors. The headline result was an artifact.

Dropping the rubric entirely is a weaker version of this control. The permutation is the one that bites.

### 5.2 Equal-effort budget

Budget the same number of tuning passes to each arm. Iterate on a validation split, freeze before scoring, never touch the test set. The temptation is to refine the Jev rubric until it looks good while handing NLI whatever hypothesis template was written first — that measures effort allocation, not model capability.

### 5.3 Corpus independence


Generate documents **independently of the rubric**, or better, apply the rubric to pre-existing real documents. Writing files to match rubric clauses leaks the answer into the corpus.

### 5.4 Cardinality parity

Keep the tree shallow (≤ 20 folders). Jev takes a declared option set, so a large tree forces a two-step descent (group, then folder) while the other arms score all options at once. That is exactly the like-for-like problem in the published Banking77 comparison and it muddies the result.


---

## 6. Metrics

- **Accuracy per (condition × clause type)**, with bootstrap 95% CIs.
- **Shuffle-control delta**: accuracy against permuted ground truth vs original. High = conditioning; low = priors.
- **Calibration (ECE)** on returned probabilities for `jev`, `openjev` and `haiku`. See §6.1 — this is a headline result, not a footnote.
- **Confidence at errors.** Published agent-harness work reports high scores reliable, low scores not safe. Check whether that holds here before using low confidence as an auto-reject.
- **Run-to-run variance: measure on every probabilistic arm, not just the LLM.** Jev is non-deterministic, openjev is non-deterministic, Haiku at temp 0 is non-deterministic. Three repeats per arm, report disagreement rate against the arm's own modal answer. An arm that is 2 points more accurate but disagrees with itself twice as often is not obviously better.
- **Latency and cost per document** — secondary for Part 1, primary for Part 2. Log median and p95 per arm, plus actual spend.
- **Non-determinism** (Haiku arm): variance across 3 repeats at temp 0. If the LLM disagrees with itself across runs, that is a cost of the LLM path worth quantifying.

### 6.1 Calibration comparison (the moat question)

TypeSafe's differentiating claim is RLCD — calibration as a training objective rather than a post-hoc fit. openjev reimplementations get typed outputs from frozen models with no such training. **If hosted Jev's calibration is meaningfully better than a temperature-fitted openjev, the moat is real. If a single fitted temperature closes the gap, the moat is a tuning step.**

Existing evidence suggests the latter is plausible: one reimplementation found hosted Jev itself overconfident (ECE 0.104 → 0.061 at T=1.75), with 8B needing T≈3.85 and a 27B T≈1.85 — one constant per model, fitted on ~100 labelled rows, and no single constant working for everyone.

Protocol: report ECE for each arm **both raw and after fitting one temperature constant on a held-out ~100-row split**. Comparing raw Jev against raw openjev is not the interesting comparison; comparing them after each gets its one free parameter is.

This is the single most decision-relevant number in the whole test for a firm that plans to keep a fallback path.


### Comparison framework for Part 2

Set this before looking at results — how to read each possible outcome, not a prescription for
what to do about it:

| Outcome | Read |
|---|---|
| Jev ≥ Haiku on accuracy | Same quality at ~5x speed and a fraction of the cost — a decisive result in Jev's favor. |

| Jev within ~3 points of Haiku | Close enough that price/latency become the deciding axes rather than accuracy. Quantify the gap in review workload, not accuracy points — the number that matters is how many extra items land in human review per 1,000. |
| Jev > 3 points behind, gap concentrated in type 3 | The gap is isolated to relational lookup, not general-purpose reasoning — a narrow, well-understood weakness rather than a broad one. |
| Jev > 3 points behind across all clause types | The cheap LLM path outperforms broadly; no basis to evaluate more expensive LLMs on this evidence alone. |


**Third read (openjev):** if openjev lands within a few points of hosted Jev after temperature fitting, the architecture decision changes — build against the wire API, default to hosted for convenience, keep the local server as a live fallback rather than a theoretical one. That is worth more to a consulting practice than a couple of accuracy points, because it removes single-vendor exposure from every client system built on this.


The accuracy gap is not the decision variable on its own — **cost per acceptably-classified document** is. A model 2 points worse at 1/40th the price may still win once the review threshold is set, and a model 2 points worse at the *same* effective price does not.

---

## 7. Expected result and what would falsify it

**Expected:** NLI at chance in Conditions B and C regardless of clause type. Jev degrading gracefully across the clause gradient, holding through type 3. Shuffle control showing Jev tracking permuted assignments.


**Falsifiers:**

- Jev ignores permuted rubric clauses and sorts by content priors → it is not conditioning on the rubric; the whole claim collapses.

- Jev fails Condition C (follows folder names over conflicting rubric) → it is using label semantics like a zero-shot classifier after all, just better at it.
- Jev's advantage disappears once clause wording is degraded → sensitivity to prompt engineering, not a capability difference. Worth a wording-ablation arm if time permits.

---


## 8. Known confound: rubric decomposition

Published agent-harness work found that merging two criteria into one question produced a mushy 0.47 where splitting them produced 0.04 / 0.96. Criteria decomposition is a large free parameter.


**Mitigation:** fix the decomposition granularity up front, document it, and use the same decomposition across all arms and conditions. Do not tune it per-condition. If decomposition is varied, treat it as a deliberate second factor with its own reporting, not as prompt polish.

---

## 9. Effort

- Harness: ~half a day. A published, reproducible harness exists to fork (`zhuyansen/jev-zeroshot-vs-bert`) rather than rebuilding scoring and bootstrap from scratch.
- Corpus: ~half a day if synthetic, 1–2 days if drawn from real documents.
- Runs: Jev is $0.042/M input tokens, output free — a few thousand documents is well under a dollar. The Haiku arm at 3 repeats is the actual line item, and still small; log real spend per arm, since that number *is* one of the results.
- Local arms: NLI and bge-m3 run on CPU or a single GPU in under an hour. The openjev arm needs a GPU and a ~18 GB weight download — Docker image is prebuilt, so it is a download-and-wait rather than a build. Budget an extra half day if no GPU box is already standing.

---

## 10. Scope note

This is the general-interest version of the question. A narrower and more billable framing of the same harness: *does Jev hit acceptable accuracy on [specific client sorting/routing task] at a threshold where we auto-approve above it and route the rest to human review?* Same infrastructure, different corpus, answers a question a client actually asked.
