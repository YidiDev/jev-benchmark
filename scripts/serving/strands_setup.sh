#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/strands-venv/bin:/usr/local/cuda/bin:$PATH"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
if [[ ! -d "$HOME/strands-decider/.git" ]]; then
  git clone https://github.com/strands-labs/strands-decider.git "$HOME/strands-decider"
fi
git -C "$HOME/strands-decider" checkout 3e94e9d84c620ed5a95f1a3310c3decb971e261c
uv venv "$HOME/strands-venv" --python 3.12
uv pip install --python "$HOME/strands-venv/bin/python" 'torch==2.7.1' \
  --index-url https://download.pytorch.org/whl/cu126
uv pip install --python "$HOME/strands-venv/bin/python" \
  -e "$HOME/strands-decider[cuda]" 'torch==2.7.1' \
  'flash-linear-attention==0.5.0' 'transformers==5.18.0'
MAX_JOBS=2 uv pip install --python "$HOME/strands-venv/bin/python" \
  causal-conv1d==1.7.0 --no-build-isolation
"$HOME/strands-venv/bin/python" -c \
  'from huggingface_hub import snapshot_download; snapshot_download("StrandsAgents/strands-decider-2B-hobson-v21", revision="2b52a6235c1b8306bbfa30b00b9d4b74b63a39f5", local_dir="/root/strands-checkpoint")'
"$HOME/strands-venv/bin/python" -c \
  'from huggingface_hub import snapshot_download; snapshot_download("Qwen/Qwen3.5-2B-Base", revision="b1485b2fa6dfa1287294f269f5fb618e03d52d7c")'
if [[ "${SETUP_ONLY:-0}" == 1 ]]; then exit 0; fi
exec "$HOME/strands-venv/bin/strands-decider" serve "$HOME/strands-checkpoint" \
  --device cuda --port 8099 --max-batch 4
