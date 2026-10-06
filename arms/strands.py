"""Strands Decider 2B Hobson v21, calibrated pointer head.

Keep the released 4,096-token window and documented default state truncation.
Whole-exam requests contain the unchanged transcript; report server truncation
as a model limitation. Run serially: upstream does not promise concurrency safety.
"""
from arms.hosted_decision import HostedDecisionArm


class StrandsArm(HostedDecisionArm):
    name = "strands"
    MODEL = "strands-decider-2B-hobson-v21"
    PRICING_KEY = "strands-decider-2b"
    ENV_PREFIX = "STRANDS"
