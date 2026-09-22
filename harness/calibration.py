"""Calibration metrics: Expected Calibration Error (ECE), raw and with a
single fitted temperature parameter, per test-plan.md §6 ("the single most
decision-relevant number... for a firm that plans to keep a fallback
path"). Only meaningful for arms with a genuine per-call confidence
estimate (jev, haiku, openjev) -- nli-bart/emb-bge's confidence-like scores
are documented as uncalibrated in their own modules and excluded from this
report.
"""

from __future__ import annotations

import math

Pair = tuple[float, bool]  # (confidence, was_correct)


def _logit(p: float, eps: float = 1e-6) -> float:
    p = min(max(p, eps), 1 - eps)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def apply_temperature(confidence: float, temperature: float) -> float:
    """Rescale a scalar confidence by temperature T via its logit -- the
    scalar analogue of softmax temperature scaling, since none of these
    arms' `confidence` fields are a full per-class softmax we could scale
    directly (Jev's is a formula-derived convenience value, Haiku's is
    self-reported)."""
    return _sigmoid(_logit(confidence) / temperature)


def ece(pairs: list[Pair], n_bins: int = 10) -> float:
    """Standard equal-width-bin Expected Calibration Error:
    sum_over_bins( |bin_size| / N * |avg_confidence_in_bin - accuracy_in_bin| )."""
    if not pairs:
        return 0.0
    bins: list[list[Pair]] = [[] for _ in range(n_bins)]
    for conf, correct in pairs:
        idx = min(int(conf * n_bins), n_bins - 1)
        bins[idx].append((conf, correct))

    n = len(pairs)
    total = 0.0
    for bucket in bins:
        if not bucket:
            continue
        bucket_n = len(bucket)
        avg_conf = sum(c for c, _ in bucket) / bucket_n
        acc = sum(1 for _, correct in bucket if correct) / bucket_n
        total += (bucket_n / n) * abs(avg_conf - acc)
    return total


def fit_temperature(pairs: list[Pair], t_min: float = 0.2, t_max: float = 5.0, step: float = 0.1) -> float:
    """Grid-search the single temperature T minimizing ECE on `pairs`
    (intended to be a held-out/validation split, per test-plan.md §6)."""
    if not pairs:
        return 1.0
    best_t, best_ece = 1.0, float("inf")
    t = t_min
    while t <= t_max + 1e-9:
        adjusted = [(apply_temperature(c, t), correct) for c, correct in pairs]
        e = ece(adjusted)
        if e < best_ece:
            best_ece, best_t = e, t
        t += step
    return best_t
