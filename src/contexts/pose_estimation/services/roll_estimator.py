from __future__ import annotations

from statistics import mean

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.pose_estimation.domain.roll_estimate import RollEstimate
from src.shared.math_utils import clamp, weighted_median


def estimate_roll(feature_set: LineFeatureSet) -> RollEstimate:
    candidates: list[float] = []
    weights: list[float] = []

    for line in feature_set.near_horizontal_lines:
        candidates.append(line.angle_deg)
        weights.append(line.length)

    for line in feature_set.near_vertical_lines:
        candidates.append(_vertical_deviation(line))
        weights.append(line.length)

    roll = weighted_median(candidates, weights)
    if roll is None:
        return RollEstimate(
            roll=None,
            confidence=0.0,
            unit="degree",
            method="line_orientation_based_roll_estimation",
            candidate_count=0,
        )

    confidence = _confidence(candidates, weights, roll)
    camera_roll = -roll
    return RollEstimate(
        roll=round(camera_roll, 2),
        confidence=round(confidence, 2),
        unit="degree",
        method="line_orientation_based_roll_estimation",
        candidate_count=len(candidates),
    )


def candidate_lines(feature_set: LineFeatureSet) -> list[LineSegment]:
    return feature_set.near_horizontal_lines + feature_set.near_vertical_lines


def roll_candidate_angle(line: LineSegment) -> float:
    if line.orientation == "near_vertical":
        return _vertical_deviation(line)
    return line.angle_deg


def _vertical_deviation(line: LineSegment) -> float:
    if line.angle_deg >= 0:
        return line.angle_deg - 90.0
    return line.angle_deg + 90.0


def _confidence(candidates: list[float], weights: list[float], roll: float) -> float:
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0

    count_score = clamp(len(candidates) / 10.0, 0.0, 1.0)
    average_weight = mean(weights)
    length_score = clamp(average_weight / 180.0, 0.0, 1.0)
    weighted_spread = sum(abs(angle - roll) * weight for angle, weight in zip(candidates, weights)) / total_weight
    concentration_score = clamp(1.0 - (weighted_spread / 20.0), 0.0, 1.0)
    return clamp((0.35 * count_score) + (0.25 * length_score) + (0.40 * concentration_score), 0.0, 1.0)
