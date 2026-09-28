"""Provisions/tears down the single rented RunPod GPU used to self-host
Kev-4B, Nimble-9B, and CLM-8B sequentially (see methodology.md §18).

Not part of the benchmark's own dependencies (runpod isn't in pyproject.toml
-- this is a one-off ops script, run via `uv run --with runpod python -m
scripts.serving.runpod_provision ...`, not something arms/harness code ever
imports). Requires RUNPOD_API_KEY in .env.

One pod, reused for all three models in sequence (Kev -> Nimble -> CLM),
then terminated -- not three separate rentals -- to minimize idle-GPU
billing and total session overhead. See scripts/serving/README.md for the
full step-by-step workflow this script is one piece of.

Usage:
    uv run --with runpod python -m scripts.serving.runpod_provision create
    uv run --with runpod python -m scripts.serving.runpod_provision status --pod-id <id>
    uv run --with runpod python -m scripts.serving.runpod_provision terminate --pod-id <id>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import runpod

import harness.env  # noqa: F401 -- loads .env (RUNPOD_API_KEY)

GPU_TYPE = "NVIDIA RTX A6000"  # 48GB, comfortably fits Kev-4B (~9GB), Nimble-9B merged (~18-20GB), CLM's Qwen3-8B vLLM pooling server (~16GB) one at a time
CLOUD_TYPE = "COMMUNITY"  # $0.33/hr vs SECURE's $0.53/hr -- see methodology.md §18 pricing snapshot
IMAGE = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
CONTAINER_DISK_GB = 80  # torch/vllm/transformers + 3 checkpoints (~9+20+16GB) with headroom
PORTS = "22/tcp,8009/http,8010/http,8700/http,8090/http"  # ssh, kev, nimble-wrapper, clm-serve, clm's vllm backend


def _ssh_public_key() -> str:
    path = os.path.expanduser(os.environ.get("SSH_PUBLIC_KEY_PATH", "~/.ssh/id_ed25519.pub"))
    return open(path).read().strip()


def create(name: str = "jev-benchmark-new-arms", gpu_type: str = GPU_TYPE, cloud_type: str = CLOUD_TYPE) -> dict:
    runpod.api_key = os.environ["RUNPOD_API_KEY"]
    pod = runpod.create_pod(
        name=name,
        image_name=IMAGE,
        gpu_type_id=gpu_type,
        cloud_type=cloud_type,
        gpu_count=1,
        container_disk_in_gb=CONTAINER_DISK_GB,
        ports=PORTS,
        support_public_ip=True,
        start_ssh=True,
        env={"PUBLIC_KEY": _ssh_public_key()},
    )
    print(json.dumps(pod, indent=2))
    return pod


def status(pod_id: str) -> dict:
    runpod.api_key = os.environ["RUNPOD_API_KEY"]
    pod = runpod.get_pod(pod_id)
    print(json.dumps(pod, indent=2))
    return pod


def wait_until_running(pod_id: str, timeout_s: int = 300) -> dict:
    runpod.api_key = os.environ["RUNPOD_API_KEY"]
    start = time.time()
    while time.time() - start < timeout_s:
        pod = runpod.get_pod(pod_id)
        if pod.get("desiredStatus") == "RUNNING" and pod.get("runtime"):
            print(json.dumps(pod, indent=2))
            return pod
        print(f"waiting... status={pod.get('desiredStatus')}")
        time.sleep(10)
    raise TimeoutError(f"pod {pod_id} did not reach RUNNING within {timeout_s}s")


def terminate(pod_id: str) -> None:
    runpod.api_key = os.environ["RUNPOD_API_KEY"]
    runpod.terminate_pod(pod_id)
    print(f"terminated {pod_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create")
    p_status = sub.add_parser("status")
    p_status.add_argument("--pod-id", required=True)
    p_wait = sub.add_parser("wait")
    p_wait.add_argument("--pod-id", required=True)
    p_term = sub.add_parser("terminate")
    p_term.add_argument("--pod-id", required=True)
    args = parser.parse_args()

    if args.cmd == "create":
        create()
    elif args.cmd == "status":
        status(args.pod_id)
    elif args.cmd == "wait":
        wait_until_running(args.pod_id)
    elif args.cmd == "terminate":
        terminate(args.pod_id)
    else:
        print(f"unknown command {args.cmd!r}", file=sys.stderr)
        sys.exit(1)
