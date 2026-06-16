from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from statistics import median

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.geometry_features.domain.vanishing_point import VanishingPoint
from src.contexts.geometry_features.domain.vanishing_point_cluster import VanishingPointCluster
from src.contexts.geometry_features.domain.vanishing_point_feature_set import VanishingPointFeatureSet
from src.shared.math_utils import clamp


@dataclass(frozen=True)
class VanishingPointDetectionConfig:
    min_perspective_lines: int = 2
    min_intersection_angle_deg: float = 4.0
    max_distance_factor: float = 4.0
    cluster_gap_factor: float = 0.18


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

    clusters = _cluster_candidates(candidates, image_width, image_height, config)
    selected_cluster = clusters[0] if clusters else None
    second_best_cluster = clusters[1] if len(clusters) > 1 else None
    if selected_cluster is None:
        return VanishingPointFeatureSet(
            perspective_lines=perspective_lines,
            candidate_points=[],
            selected_vanishing_point=None,
            confidence=0.0,
            reason="no_valid_vanishing_point_clusters",
        )

    vp_x = selected_cluster.center_x
    vp_y = selected_cluster.center_y
    spread = selected_cluster.spread
    support_radius = max(image_width, image_height) * 0.35
    support = selected_cluster.support_count
    support_score = clamp(support / 8.0, 0.0, 1.0)
    line_score = clamp(len(perspective_lines) / 8.0, 0.0, 1.0)
    spread_score = clamp(1.0 - (spread / max(max(image_width, image_height), 1.0)), 0.0, 1.0)
    confidence = clamp((0.45 * support_score) + (0.25 * line_score) + (0.30 * spread_score), 0.0, 1.0)
    line_support_consistency = clamp(support / max(len(candidates), 1), 0.0, 1.0)
    cluster_ambiguity = (
        clamp(second_best_cluster.score / max(selected_cluster.score, 1e-6), 0.0, 1.0)
        if second_best_cluster is not None
        else 0.0
    )

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
        clusters=clusters,
        selected_cluster_id=selected_cluster.cluster_id,
        second_best_cluster_id=second_best_cluster.cluster_id if second_best_cluster is not None else None,
        cluster_ambiguity=round(cluster_ambiguity, 4),
        line_support_consistency=round(line_support_consistency, 4),
    )


def _cluster_candidates(
    candidates: list[tuple[float, float]],
    image_width: int,
    image_height: int,
    config: VanishingPointDetectionConfig,
) -> list[VanishingPointCluster]:
    if not candidates:
        return []

    max_gap = max(80.0, image_width * config.cluster_gap_factor)
    sorted_points = sorted(candidates, key=lambda point: point[0])
    groups: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = [sorted_points[0]]
    for point in sorted_points[1:]:
        if abs(point[0] - median([candidate[0] for candidate in current])) <= max_gap:
            current.append(point)
        else:
            groups.append(current)
            current = [point]
    groups.append(current)

    clusters = [
        _build_cluster(cluster_id, points, image_width, image_height)
        for cluster_id, points in enumerate(groups, start=1)
    ]
    return sorted(clusters, key=lambda cluster: cluster.score, reverse=True)


def _build_cluster(
    cluster_id: int,
    points: list[tuple[float, float]],
    image_width: int,
    image_height: int,
) -> VanishingPointCluster:
    center_x = median([point[0] for point in points])
    center_y = median([point[1] for point in points])
    distances = [hypot(point[0] - center_x, point[1] - center_y) for point in points]
    spread = median(distances) if distances else 0.0
    support_score = clamp(len(points) / 12.0, 0.0, 1.0)
    spread_score = clamp(1.0 - spread / max(max(image_width, image_height), 1.0), 0.0, 1.0)
    center_y_score = clamp(1.0 - abs(center_y - (image_height / 2.0)) / max(image_height, 1.0), 0.0, 1.0)
    score = (0.55 * support_score) + (0.30 * spread_score) + (0.15 * center_y_score)
    return VanishingPointCluster(
        cluster_id=cluster_id,
        center_x=round(center_x, 2),
        center_y=round(center_y, 2),
        support_count=len(points),
        spread=round(spread, 2),
        score=round(score, 4),
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
