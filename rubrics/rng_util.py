"""Randomization helpers for anything that must be uninfluenced by semantics:
opaque folder IDs, and derangements used for the misleading condition and the
shuffle control. See methodology.md §1.
"""

from __future__ import annotations

import random
import string


def derangement(items: list, rng: random.Random) -> dict:
    """A permutation of `items` with no fixed points (item[i] never maps to
    itself), keyed by original item. Used so Condition C's "misleading"
    folder-name swap and the shuffle-control clause permutation are always
    genuinely different from identity, never accidentally reproduce it.

    Rejection-sampled: shuffle and retry until no fixed point survives.
    Fine for the small n (<=4) used in this benchmark.
    """
    if len(items) < 2:
        raise ValueError("derangement requires at least 2 items")
    pool = list(items)
    while True:
        shuffled = pool[:]
        rng.shuffle(shuffled)
        if all(a != b for a, b in zip(pool, shuffled)):
            return dict(zip(pool, shuffled))


def random_opaque_id(rng: random.Random, length: int = 6) -> str:
    """Lowercase-alnum id in the style of test-plan.md's examples
    (k2m8p1, x7f3q9, b4n0z2) -- random, not hand-picked-looking."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(rng.choice(alphabet) for _ in range(length))


def distinct_opaque_ids(rng: random.Random, n: int, length: int = 6) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    while len(out) < n:
        candidate = random_opaque_id(rng, length)
        if candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out
