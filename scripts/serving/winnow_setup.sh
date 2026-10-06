#!/usr/bin/env bash
# Source build against the host CUDA toolkit (A6000 compute capability 8.6).
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/cuda/bin:$PATH"
# RunPod's CUDA development image has nvcc, but not the native build deps.
apt-get update
apt-get install -y build-essential libssl-dev ninja-build
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install 'cmake>=3.24'
if [[ ! -d "$HOME/winnow-inference/.git" ]]; then
  git clone https://github.com/EldanRing/winnow-inference.git "$HOME/winnow-inference"
fi
git -C "$HOME/winnow-inference" checkout d4631fbf20b73e0372281a6bb5ca44322f173692
cd "$HOME/winnow-inference"
python3 scripts/winnow.py setup --model q8 --vision off --reasoning off --mtp off \
  --cuda-arch "${CUDA_ARCH:-86}"
if [[ "${SETUP_ONLY:-0}" == 1 ]]; then exit 0; fi
exec python3 scripts/winnow.py serve --model q8 --vision off --reasoning off --mtp off \
  --context 16k --host 127.0.0.1 --port 8091
