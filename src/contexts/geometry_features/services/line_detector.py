from __future__ import annotations

from dataclasses import dataclass

import cv2

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.preprocessing.domain.edge_map import EdgeMap


@dataclass(frozen=True)
class LineDetectionConfig:
    rho: float = 1.0
    theta_deg: float = 1.0
    threshold: int = 50
    min_line_length: int = 60
    max_line_gap: int = 10
    horizontal_threshold_deg: float = 20.0
    vertical_threshold_deg: float = 20.0


def detect_lines(edge_map: EdgeMap, config: LineDetectionConfig) -> LineFeatureSet:
    raw_lines = cv2.HoughLinesP(
        edge_map.edges,
        rho=config.rho,
        theta=config.theta_deg * 3.141592653589793 / 180.0,
        threshold=config.threshold,
        minLineLength=config.min_line_length,
        maxLineGap=config.max_line_gap,
    )

    detected: list[LineSegment] = []
    if raw_lines is not None:
        for raw_line in raw_lines:
            x1, y1, x2, y2 = [int(value) for value in raw_line[0]]
            detected.append(
                LineSegment.from_points(
                    x1,
                    y1,
                    x2,
                    y2,
                    config.horizontal_threshold_deg,
                    config.vertical_threshold_deg,
                )
            )

    filtered = [line for line in detected if line.length >= config.min_line_length]
    return LineFeatureSet(detected_lines=detected, filtered_lines=filtered)

