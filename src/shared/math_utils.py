from __future__ import annotations

from typing import Sequence


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float | None:
    if not values or not weights or len(values) != len(weights):
        return None

    pairs = sorted(zip(values, weights), key=lambda item: item[0])
    total_weight = sum(max(weight, 0.0) for _, weight in pairs)
    if total_weight <= 0:
        return None

    midpoint = total_weight / 2.0
    running = 0.0
    for value, weight in pairs:
        running += max(weight, 0.0)
        if running >= midpoint:
            return value
    return pairs[-1][0]

