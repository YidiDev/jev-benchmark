"""Winnow-12B Q8_0, Gemma-4-12B-it LoRA via winnow-inference.

Use the explicit Q8 target; disable optional reasoning, MTP and vision.
Native decision temperature remains 1.0.
"""
from arms.hosted_decision import HostedDecisionArm


class WinnowArm(HostedDecisionArm):
    name = "winnow"
    MODEL = "Winnow-12B"
    PRICING_KEY = "winnow-12b-q8"
    ENV_PREFIX = "WINNOW"
