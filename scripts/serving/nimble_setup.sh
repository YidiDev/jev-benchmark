#!/usr/bin/env bash
# Run ON the rented RunPod GPU box (via ssh) to set up Nimble-9B and launch
# the custom FastAPI wrapper (scripts/serving/nimble_server.py, which must
# already have been scp'd to $HOME/nimble_server.py before running this)
# that gives it a TypeSafe-shaped /v1/systemone on :8010 -- Nimble ships no
# HTTP server of its own, see that file's docstring for the full rationale.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
fi

cd "$HOME"
if [ ! -d nimble ]; then
    git clone https://github.com/bespokelabsai/nimble.git nimble
fi
cd nimble

# Nimble's own README assumes a system python3.12; not every base image
# ships one (this repo's RunPod image only has 3.11), so use uv to fetch
# and manage 3.12 instead of depending on the base image -- same approach
# kev_setup.sh already takes for its own uv-managed Python.
uv python install 3.12
uv venv .cache/venvs/nimble --python 3.12
source .cache/venvs/nimble/bin/activate
uv pip install -q torch==2.8.0 -r requirements/training.txt
uv pip install -q fastapi "uvicorn[standard]"

python - <<'PYTHON'
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

repo = "bespokelabs/Bespoke-Nimble-9B"
snapshot = Path(snapshot_download(repo, cache_dir=".cache/huggingface/hub"))
contract_file = snapshot / "schema_config.json"
contract = json.loads(contract_file.read_text()) if contract_file.exists() else {}
if contract:
    from transformers import AutoTokenizer
    from nimble.training.candidate_schema import validate_contract
    validate_contract(contract, AutoTokenizer.from_pretrained(snapshot))

model_path = snapshot
if (snapshot / "adapter_config.json").exists():
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

    base = Qwen3_5ForConditionalGeneration.from_pretrained(
        contract["model"], revision=contract["revision"],
        dtype=torch.bfloat16, device_map="cpu",
    )
    adapter = PeftModel.from_pretrained(base, snapshot)
    merged = adapter.merge_and_unload(safe_merge=True)
    model_path = Path(".cache/models") / ("nimble-9b-" + snapshot.name)
    merged.save_pretrained(model_path)
    (model_path / "schema_config.json").write_text(json.dumps(contract, indent=2))
    AutoTokenizer.from_pretrained(snapshot).save_pretrained(model_path)
    (model_path / "READY.json").write_text(json.dumps({
        "model": repo, "revision": snapshot.name,
        "adapter_sha256": hashlib.sha256(
            (snapshot / "adapter_model.safetensors").read_bytes()
        ).hexdigest(),
    }, indent=2))

config = {
    "model_path": str(model_path.resolve()),
    "model_id": repo,
    "revision": snapshot.name,
    "max_input_tokens": contract.get("max_length", 2048),
}
Path(".cache/nimble-model.json").write_text(json.dumps(config, indent=2))
print("Ready:", model_path)
PYTHON

if [ ! -f "$HOME/nimble_server.py" ] || [ ! -f "$HOME/nimble_schema.py" ]; then
    echo "ERROR: $HOME/nimble_server.py and/or nimble_schema.py not found -- scp both to the pod first" >&2
    exit 1
fi

cd "$HOME/nimble"
NIMBLE_MODEL_CONFIG="$HOME/nimble/.cache/nimble-model.json" \
    nohup .cache/venvs/nimble/bin/python "$HOME/nimble_server.py" \
    > "$HOME/nimble_serve.log" 2>&1 &
echo "nimble wrapper starting (pid $!), logging to ~/nimble_serve.log"

for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8010/health >/dev/null 2>&1; then
        echo "nimble wrapper is up on :8010"
        exit 0
    fi
    sleep 5
done
echo "nimble wrapper did not come up within 5 minutes -- check ~/nimble_serve.log" >&2
exit 1
