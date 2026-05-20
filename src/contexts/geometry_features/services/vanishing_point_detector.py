from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from statistics import median

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.geometry_features.domain.vanishing_point import VanishingPoint
from src.contexts.geometry_features.domain.vanishing_point_feature_set import VanishingPointFeatureSet
from src.shared.math_utils import clamp


@dataclass(frozen=True)
class VanishingPointDetectionConfig:
    min_perspective_lines: int = 2
    min_intersection_angle_deg: float = 4.0
    max_distance_factor: float = 4.0


def detect_vanishing_point(
    line_features: LineFeatureSet,
    image_width: int,
    image_height: int,
    config: VanishingPointDetectionConfig | None = None,
) -> VanishingPointFeatureSet:
    config = config or VanishingPointDetectionConfig()
    perspective_lines = [
        line for line in line_features.filtered_lines
        if line.orientation == "diagonal"
    ]
    if len(perspective_lines) < config.min_perspective_lines:
        return VanishingPointFeatureSet(
            perspective_lines=perspective_lines,
            candidate_points=[],
            selected_vanishing_point=None,
            confidence=0.0,
            reason="insufficient_perspective_lines",
        )

    candidates: list[tuple[float, float]] = []
    max_distance = max(image_width, image_height) * config.max_distance_factor
    center_x = image_width / 2.0
    center_y = image_height / 2.0
    for index, first in enumerate(perspective_lines):
        for second in perspective_lines[index + 1:]:
            if abs(first.angle_deg - second.angle_deg) < config.min_intersection_angle_deg:
                continue
            point = _intersection(first, second)
            if point is None:
                continue
            x, y = point
            if abs(x - center_x) > max_distance or abs(y - center_y) > max_distance:
                continue
            candidates.append(point)

    if not candidates:
        return VanishingPointFeatureSet(
            perspective_lines=perspective_lines,
            candidate_points=[],
            selected_vanishing_point=None,
            confidence=0.0,
            reason="no_valid_vanishing_point_intersections",
        )

    vp_x = median([point[0] for point in candidates])
    vp_y = median([point[1] for point in candidates])
    distances = [hypot(point[0] - vp_x, point[1] - vp_y) for point in candidates]
    spread = median(distances) if distances else 0.0
    support_radius = max(image_width, image_height) * 0.35
    support = sum(1 for distance in distances if distance <= support_radius)
    support_score = clamp(support / 8.0, 0.0, 1.0)
    line_score = clamp(len(perspective_lines) / 8.0, 0.0, 1.0)
    spread_score = clamp(1.0 - (spread / max(max(image_width, image_height), 1.0)), 0.0, 1.0)
    confidence = clamp((0.45 * support_score) + (0.25 * line_score) + (0.30 * spread_score), 0.0, 1.0)

    point = VanishingPoint(
        x=round(vp_x, 2),
        y=round(vp_y, 2),
        confidence=round(confidence, 2),
        support_count=support,
        spread=round(spread, 2),
    )
    return VanishingPointFeatureSet(
        perspective_lines=perspective_lines,
        candidate_points=candidates,
        selected_vanishing_point=point,
        confidence=point.confidence,
    )


def _intersection(first: LineSegment, second: LineSegment) -> tuple[float, float] | None:
    x1, y1, x2, y2 = first.x1, first.y1, first.x2, first.y2
    x3, y3, x4, y4 = second.x1, second.y1, second.x2, second.y2
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1e-6:
        return None

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    return px, py
