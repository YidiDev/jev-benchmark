#!/usr/bin/env bash
# Run ON the rented RunPod GPU box (via ssh) to set up and launch CLM-8B's
# own clm-serve on top of a vLLM Qwen3-8B pooling backend, per
# github.com/Contrastive-LM/CLM's own README. Exposes a real TypeSafe-
# compatible /v1/systemone on :8700 (vLLM's embedding server on :8090 is
# internal-only, called by clm-serve, not by arms/nimble-style clients).
#
# Both raised to 8192 tokens (from CLM's 2,048-token default) together, per
# methodology.md §18: CT9's k=10 combined form + subtree-description text
# runs to ~3,100 tokens at points, above the 2,048 default.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
fi

cd "$HOME"
# Base image only ships python3.11 -- same fix as nimble_setup.sh, use
# uv-managed 3.12 instead of depending on the base image.
uv python install 3.12
uv venv .cache/venvs/clm --python 3.12
source .cache/venvs/clm/bin/activate
uv pip install -q "contrastive-lm[serve,vllm]"

nohup .cache/venvs/clm/bin/vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b \
    --runner pooling --max-model-len 8192 --port 8090 \
    > "$HOME/clm_vllm.log" 2>&1 &
echo "vllm embedding backend starting (pid $!), logging to ~/clm_vllm.log"

for _ in $(seq 1 120); do
    if curl -sf http://127.0.0.1:8090/v1/models >/dev/null 2>&1; then
        echo "vllm backend is up on :8090"
        break
    fi
    sleep 5
done

nohup .cache/venvs/clm/bin/clm-serve --port 8700 --max-tokens 8192 \
    --emb-url http://127.0.0.1:8090/v1/embeddings --emb-model qwen3-8b \
    --action-cache 512MiB \
    > "$HOME/clm_serve.log" 2>&1 &
echo "clm-serve starting (pid $!), logging to ~/clm_serve.log"

for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8700/v1/models >/dev/null 2>&1; then
        echo "clm-serve is up on :8700"
        exit 0
    fi
    sleep 5
done
echo "clm-serve did not come up within 5 minutes -- check ~/clm_serve.log and ~/clm_vllm.log" >&2
exit 1
