# Cygnet / Winnow-Q8 / Strands Decider: CT1–10

These servers use isolated environments on a rented NVIDIA GPU. The benchmark
client needs no additional dependencies. Use one server at a time; Strands
requests in particular must be serial. Source pins are in the setup scripts.

| Arm | Weights | Runtime | Context policy |
|---|---|---|---|
| `cygnet` | Frozen `google/gemma-4-12B-it`, revision `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | vLLM 0.30.0 + upstream application decision server, T=3.4 | 16,384 tokens; refuses over-limit prompts |
| `winnow` | Explicit `Winnow-12B-Q8_0.gguf`, verified by upstream release manifest | Pinned winnow-inference source build; direct T=1, vision/reasoning/MTP off | Configured 16K; no client truncation |
| `strands` | `StrandsAgents/strands-decider-2B-hobson-v21`, revision `2b52a6235c1b8306bbfa30b00b9d4b74b63a39f5` | Pinned strands-decider source, released calibration | Released 4,096-token window, native default state truncation |

On the GPU box run `bash cygnet_setup.sh`, `bash winnow_setup.sh`, or
`bash strands_setup.sh`. Winnow builds for compute capability 86 (A6000);
set `CUDA_ARCH` for other cards. Cygnet needs a driver supporting its vLLM
CUDA wheel. Setup can require accepting any applicable model-access terms.

Connect the benchmark client through SSH tunnels:

```bash
ssh -N -L 18010:127.0.0.1:8010 -L 18091:127.0.0.1:8091 \
  -L 18099:127.0.0.1:8099 -p PORT root@GPU_HOST
```

Set `CYGNET_BASE_URL=http://127.0.0.1:18010`,
`WINNOW_BASE_URL=http://127.0.0.1:18091`, and
`STRANDS_BASE_URL=http://127.0.0.1:18099` in `.env` or the environment.
If using authentication, set the corresponding `*_API_KEY` too.

Run the unchanged full grids for each arm:

```bash
uv run python -m scripts.run_api_arm --arm cygnet --repeats 1
uv run python -m qtree.runner --arm cygnet --repeats 1
uv run python -m examgrade.runner --arm cygnet
```

Repeat with `winnow` and `strands`. CT1–8 includes separate A/B/C/SHUFFLE
calls; CT9 includes all k values and both k=10 labelings; CT10 includes both
key conditions and chained/whole-exam modes. Expected output per arm:
1,920 document rows, 1,140 tree chunks, and 12,000 question-grade rows.

One pass is the primary grid for these deterministic readouts. Near-tie
numerical changes can still arise from precision or batch order; this does
not establish exact bitwise reproducibility. Keep serving settings fixed.

The client allows 600 seconds per request so cold CUDA autotuning can finish
without a premature retry overlapping the server's mutable engine state. The
tested Strands environment uses Torch 2.7.1+cu126, Triton 3.3.1, Transformers
5.18.0, flash-linear-attention 0.5.0 and causal-conv1d 1.7.0. Its base weights
are pinned to `b1485b2fa6dfa1287294f269f5fb618e03d52d7c` by checkpoint provenance.
Whole-exam questions use the native prefix path in groups of at most four.

All calls log real token usage through `record_spend`, with zero API-token
charges. Rented GPU charges are real infrastructure spend, tracked separately;
they are never presented as free compute or charged against Anthropic's budget.
Terminate the pod immediately after completing the evaluations.

## Interpretation fixed before results

- Cygnet tests whether a strong frozen model with decision readout transfers
  beyond the previous generated-answer Claude baselines.
- Winnow versus Cygnet compares complete released systems sharing a base.
  Precision, prompting, backend, calibration and prefix handling differ;
  accuracy differences cannot be attributed solely to fine-tuning.
- Strands tests a small deployable alternative, including native confidence
  discrimination on errors. CT8/CT10 truncation is a limitation of the released
  serving contract, not evidence about performance at an enlarged window.
- Published JevBench composite ranks are not accuracy rankings and do not
  establish parity on this corpus. No rubric or calibration tuning on test
  labels is performed.
