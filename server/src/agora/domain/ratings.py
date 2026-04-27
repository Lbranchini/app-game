"""ELO rating math.

Pure function so the result is fully testable without any DB or framework.
The K-factor is fixed at 32 for now — competitive chess reduces K for
high-rated players; we'll add a tier system once we have enough matches
to know whether it matters.
"""

from __future__ import annotations

from dataclasses import dataclass

K_FACTOR = 32


@dataclass(frozen=True)
class RatingChange:
    new_a: int
    new_b: int
    delta_a: int
    delta_b: int


def compute_new_ratings(rating_a: int, rating_b: int, winner: str | None) -> RatingChange:
    """Compute the post-match ratings using the standard ELO formula.

    `winner` is `"A"`, `"B"`, or `None` for a draw.
    """
    expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
    expected_b = 1.0 - expected_a

    score_a = 0.5 if winner is None else (1.0 if winner == "A" else 0.0)
    score_b = 1.0 - score_a

    new_a = rating_a + K_FACTOR * (score_a - expected_a)
    new_b = rating_b + K_FACTOR * (score_b - expected_b)

    rounded_a = int(round(new_a))
    rounded_b = int(round(new_b))
    return RatingChange(
        new_a=rounded_a,
        new_b=rounded_b,
        delta_a=rounded_a - rating_a,
        delta_b=rounded_b - rating_b,
    )
