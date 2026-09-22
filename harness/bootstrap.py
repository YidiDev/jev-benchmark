"""Bootstrap confidence intervals for accuracy metrics.

Uses harness.constants.sub_rng to seed a numpy Generator per (arm, clause
type, condition) bucket, so every CI in results.md is exactly reproducible
from (MASTER_SEED, purpose) alone, consistent with the RNG discipline used
everywhere else in this benchmark (see methodology.md §1) -- resampling
itself uses numpy for speed, but the seed is drawn from our own
deterministic stream rather than numpy's global state.
"""

from __future__ import annotations

import numpy as np

from harness.constants import sub_rng


def bootstrap_ci(
    values: list[bool],
    purpose: str,
    n_boot: int = 2000,
    ci: float = 0.95,
) -> tuple[float, float]:
    """Percentile bootstrap CI on the mean of a list of booleans (i.e. an
    accuracy rate). Returns (lo, hi). (0.0, 0.0) for an empty input."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)

    rng = sub_rng(purpose)
    seed = rng.randrange(2**31)
    np_rng = np.random.default_rng(seed)

    arr = np.asarray(values, dtype=float)
    idx = np_rng.integers(0, n, size=(n_boot, n))
    boot_means = arr[idx].mean(axis=1)

    alpha = (1 - ci) / 2
    lo, hi = np.quantile(boot_means, [alpha, 1 - alpha])
    return float(lo), float(hi)
