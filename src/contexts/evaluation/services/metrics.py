from __future__ import annotations

import math
from statistics import mean, median
from typing import Any

import numpy as np

from .rotation_error import geodesic_error_deg


def precision_at_theta(rows: list[dict[str, Any]], theta_deg: float) -> float | None:
    errors = values(rows, "geodesic_error_deg")
    return _ratio(sum(error <= theta_deg for error in errors), len(errors))


def recall_at_theta(rows: list[dict[str, Any]], theta_deg: float) -> float | None:
    errors = values(rows, "geodesic_error_deg")
    return _ratio(sum(error <= theta_deg for error in errors), len(rows))


def geodesic_mae(rows: list[dict[str, Any]]) -> float | None:
    errors = values(rows, "geodesic_error_deg")
    return mean(errors) if errors else None


def p95_error(rows: list[dict[str, Any]]) -> float | None:
    errors = values(rows, "geodesic_error_deg")
    return float(np.percentile(errors, 95)) if errors else None


def error_jitter(rows: list[dict[str, Any]]) -> float | None:
    valid = [row for row in rows if row.get("pose_valid")]
    changes = []
    for previous, current in zip(valid, valid[1:]):
        if current["frame_index"] != previous["frame_index"] + 1:
            continue
        changes.append(
            geodesic_error_deg(
                (current["yaw_error"], current["pitch_error"], current["roll_error"]),
                (previous["yaw_error"], previous["pitch_error"], previous["roll_error"]),
            )
        )
    return math.sqrt(mean(value * value for value in changes)) if changes else None


def axis_statistics(rows: list[dict[str, Any]], axis: str) -> dict[str, float | None]:
    errors = values(rows, f"{axis}_error")
    absolute = [abs(value) for value in errors]
    return {
        "mae": mean(absolute) if absolute else None,
        "median_absolute_error": median(absolute) if absolute else None,
        "max_absolute_error": max(absolute) if absolute else None,
        "rmse": math.sqrt(mean(value * value for value in errors)) if errors else None,
    }


def values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None
