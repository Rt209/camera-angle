from __future__ import annotations

from dataclasses import dataclass

from src.contexts.geometry_features.domain.horizon_feature_set import HorizonFeatureSet
from src.contexts.geometry_features.domain.horizon_line import HorizonLine
from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.shared.math_utils import clamp, weighted_median


@dataclass(frozen=True)
class HorizonDetectionConfig:
    min_candidates: int = 1
    max_angle_abs_deg: float = 15.0
    min_total_length_ratio: float = 0.15
    min_center_band_ratio: float = 0.35
    max_center_band_ratio: float = 0.65


def detect_horizon(
    line_features: LineFeatureSet,
    image_width: int,
    image_height: int,
    config: HorizonDetectionConfig | None = None,
) -> HorizonFeatureSet:
    config = config or HorizonDetectionConfig()
    center_x = image_width / 2.0
    min_y = image_height * config.min_center_band_ratio
    max_y = image_height * config.max_center_band_ratio
    candidates = [
        line for line in line_features.near_horizontal_lines
        if abs(line.angle_deg) <= config.max_angle_abs_deg
        and min_y <= _line_y_at_x(line, center_x) <= max_y
    ]
    if len(candidates) < config.min_candidates:
        return HorizonFeatureSet(
            candidates=candidates,
            selected_horizon=None,
            confidence=0.0,
            reason="insufficient_horizon_candidates",
        )

    y_values = [_line_y_at_x(line, center_x) for line in candidates]
    weights = [line.length for line in candidates]
    horizon_y = weighted_median(y_values, weights)
    if horizon_y is None:
        return HorizonFeatureSet(
            candidates=candidates,
            selected_horizon=None,
            confidence=0.0,
            reason="unstable_horizon_candidates",
        )

    representative = _closest_line(candidates, center_x, horizon_y)
    angle = representative.angle_deg
    slope = _line_slope(representative)
    y1 = int(round(horizon_y - slope * center_x))
    y2 = int(round(horizon_y + slope * (image_width - 1 - center_x)))
    total_weight = max(sum(weights), 1.0)
    spread = sum(abs(value - horizon_y) * weight for value, weight in zip(y_values, weights)) / total_weight
    total_length = sum(weights)
    length_score = clamp(total_length / max(image_width * config.min_total_length_ratio, 1.0), 0.0, 1.0)
    count_score = clamp(len(candidates) / 5.0, 0.0, 1.0)
    angle_score = clamp(1.0 - (abs(angle) / max(config.max_angle_abs_deg, 1.0)), 0.0, 1.0)
    spread_score = clamp(1.0 - (spread / max(image_height * 0.15, 1.0)), 0.0, 1.0)
    confidence = clamp(
        (0.25 * count_score) + (0.30 * length_score) + (0.20 * angle_score) + (0.25 * spread_score),
        0.0,
        1.0,
    )

    horizon = HorizonLine(
        x1=0,
        y1=y1,
        x2=image_width - 1,
        y2=y2,
        angle_deg=round(angle, 2),
        y_at_center=round(horizon_y, 2),
        confidence=round(confidence, 2),
        support_count=len(candidates),
    )
    return HorizonFeatureSet(
        candidates=candidates,
        selected_horizon=horizon,
        confidence=horizon.confidence,
    )


def _line_y_at_x(line: LineSegment, x: float) -> float:
    dx = line.x2 - line.x1
    if dx == 0:
        return (line.y1 + line.y2) / 2.0
    slope = (line.y2 - line.y1) / dx
    return line.y1 + slope * (x - line.x1)


def _line_slope(line: LineSegment) -> float:
    dx = line.x2 - line.x1
    if dx == 0:
        return 0.0
    return (line.y2 - line.y1) / dx


def _closest_line(candidates: list[LineSegment], center_x: float, horizon_y: float) -> LineSegment:
    return min(candidates, key=lambda line: abs(_line_y_at_x(line, center_x) - horizon_y))
