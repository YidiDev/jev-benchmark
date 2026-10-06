"""Frozen Gemma-4-12B-it, Cygnet letter-logit readout, T=3.4.

Use the upstream decision_server.py for native named multi-question support.
This released-system comparison does not isolate fine-tuning from backend,
precision, prompt or calibration differences against Winnow.
"""
from arms.hosted_decision import HostedDecisionArm


class CygnetArm(HostedDecisionArm):
    name = "cygnet"
    MODEL = "cygnet"
    PRICING_KEY = "cygnet-12b"
    ENV_PREFIX = "CYGNET"
