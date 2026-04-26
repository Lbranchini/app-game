"""Gerador de números pseudoaleatórios determinístico (para replays e testes)."""

from __future__ import annotations

import random


class SeededRng:
    """Wrapper fino sobre random.Random com seed garantida.

    Usado para que mesma seed + mesmas ações produza mesmo resultado.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self.seed = seed

    def choice(self, options: list[str]) -> str:
        return self._rng.choice(options)

    def choices(self, options: list[str], k: int) -> list[str]:
        return [self._rng.choice(options) for _ in range(k)]

    def randint(self, lo: int, hi: int) -> int:
        return self._rng.randint(lo, hi)
