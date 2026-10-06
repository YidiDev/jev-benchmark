#!/usr/bin/env bash
# Run on the GPU host; connect the benchmark client through an SSH tunnel.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/cygnet-venv/bin:/usr/local/cuda/bin:$PATH"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv venv "$HOME/cygnet-venv" --python 3.12
uv pip install --python "$HOME/cygnet-venv/bin/python" 'vllm==0.30.0'
# vLLM's CUDA 13 FlashInfer sampler cannot JIT with this image's CUDA 12.4
# toolkit. The native sampler preserves the letter-logit decision readout.
export VLLM_USE_FLASHINFER_SAMPLER=0
if [[ ! -d "$HOME/cygnet-recipe/.git" ]]; then
  git clone https://github.com/blockbrain-ai/cygnet-recipe.git "$HOME/cygnet-recipe"
fi
git -C "$HOME/cygnet-recipe" checkout 10b4099a61e7dca6a82032b54c74dc0a8c496d4b
setsid "$HOME/cygnet-venv/bin/vllm" serve google/gemma-4-12B-it \
  --revision 707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7 \
  --served-model-name cygnet --host 127.0.0.1 --port 8890 \
  --max-model-len 16384 --gpu-memory-utilization 0.90 \
  > "$HOME/cygnet-vllm.log" 2>&1 < /dev/null &
export SHIM_VLLM=http://127.0.0.1:8890/v1/chat/completions
export SHIM_MODEL=cygnet SHIM_TEMPERATURE=3.4 CYGNET_PORT=8010
setsid python3 "$HOME/cygnet-recipe/shim/decision_server.py" \
  > "$HOME/cygnet-server.log" 2>&1 < /dev/null &
wait
