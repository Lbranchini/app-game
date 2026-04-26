"""Seeded RNG implementation of the RandomSource port."""

from __future__ import annotations

import random


class SeededRandom:
    """Deterministic RandomSource backed by random.Random.

    Identical seeds produce identical sequences — required for replay and
    reproducible balance simulations.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self.seed = seed

    def choice(self, options: list[str]) -> str:
        return self._rng.choice(options)

    def randint(self, lo: int, hi: int) -> int:
        return self._rng.randint(lo, hi)
