#!/usr/bin/env bash
# Run ON the rented RunPod GPU box (via ssh) to set up and launch Kev-4B's
# own kev.serve, exactly per github.com/jaredpalmer/kev's own README quick
# start. Exposes /v1/systemone on :8009, TypeSafe-wire-compatible.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
fi

cd "$HOME"
if [ ! -d kev ]; then
    git clone https://github.com/jaredpalmer/kev.git
fi
cd kev
uv sync --extra serve

nohup uv run --extra serve python -m kev.serve --run jaredpalmer/kev-4b --host 0.0.0.0 --port 8009 \
    > "$HOME/kev_serve.log" 2>&1 &
echo "kev.serve starting (pid $!), logging to ~/kev_serve.log"

for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8009/v1/models >/dev/null 2>&1; then
        echo "kev.serve is up on :8009"
        exit 0
    fi
    sleep 5
done
echo "kev.serve did not come up within 5 minutes -- check ~/kev_serve.log" >&2
exit 1
