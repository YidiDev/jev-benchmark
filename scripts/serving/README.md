# Self-hosted GPU serving (Kev-4B, Nimble-9B, CLM-8B)

One rented RunPod GPU, reused sequentially for all three models, then
terminated. See methodology.md §18 for the full writeup and real
cost/timing log; this is the mechanical how-to.

## 1. Provision

```bash
uv run --with runpod python -m scripts.serving.runpod_provision create
# note the returned pod id
uv run --with runpod python -m scripts.serving.runpod_provision wait --pod-id <id>
```

Get the SSH connection command and HTTP proxy URLs from the RunPod
dashboard (or `status --pod-id <id>`, which prints the raw pod object
including `runtime.ports`). Each exposed port gets a URL of the form
`https://<pod-id>-<port>.proxy.runpod.net`.

## 2. Kev-4B

```bash
scp scripts/serving/kev_setup.sh root@<ssh-host>:~/kev_setup.sh
ssh root@<ssh-host> 'bash ~/kev_setup.sh'
```

Then locally:

```bash
# in .env:
KEV_BASE_URL=https://<pod-id>-8009.proxy.runpod.net

uv run python -m scripts.run_api_arm --arm kev
uv run python -m qtree.runner --arm kev
uv run python -m examgrade.runner --arm kev
```

## 3. Nimble-9B

```bash
scp scripts/serving/nimble_server.py scripts/serving/nimble_schema.py root@<ssh-host>:~/
scp scripts/serving/nimble_setup.sh root@<ssh-host>:~/nimble_setup.sh
ssh root@<ssh-host> 'bash ~/nimble_setup.sh'
```

Then locally:

```bash
# in .env:
NIMBLE_BASE_URL=https://<pod-id>-8010.proxy.runpod.net

uv run python -m scripts.run_api_arm --arm nimble
uv run python -m qtree.runner --arm nimble
uv run python -m examgrade.runner --arm nimble --modes chained   # whole_exam unsupported, see examgrade/arms.py
```

## 4. CLM-8B (CT9 only)

```bash
scp scripts/serving/clm_setup.sh root@<ssh-host>:~/clm_setup.sh
ssh root@<ssh-host> 'bash ~/clm_setup.sh'
```

Then locally:

```bash
# in .env:
CLM_BASE_URL=https://<pod-id>-8700.proxy.runpod.net

uv run python -m qtree.runner --arm clm
```

## 5. Teardown

```bash
uv run --with runpod python -m scripts.serving.runpod_provision terminate --pod-id <id>
```

Do this immediately after CLM's CT9 run finishes -- billing is per-hour
while the pod exists, whether or not a server on it is actively serving
requests.

## Notes

- Only one of the three servers needs to be running at a time (they're
  evaluated sequentially: Kev, then Nimble, then CLM), so each `_setup.sh`
  assumes the previous one's process is still fine to leave running in the
  background (they're on different ports and the GPU has headroom for all
  three's *inference* memory simultaneously, just not worth the complexity
  of stopping/starting between phases).
- If a setup script's health-check loop times out, the model download
  (Kev-4B ~9GB, Nimble-9B's base+adapter ~20GB, Qwen3-8B ~16GB) is the most
  likely cause on a slow link -- check the referenced `.log` file before
  assuming a real failure.
