from __future__ import annotations

from dataclasses import dataclass

from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.geometry_features.domain.vanishing_point import VanishingPoint
from src.contexts.geometry_features.domain.vanishing_point_cluster import VanishingPointCluster


@dataclass(frozen=True)
class VanishingPointFeatureSet:
    perspective_lines: list[LineSegment]
    candidate_points: list[tuple[float, float]]
    selected_vanishing_point: VanishingPoint | None
    confidence: float
    clusters: list[VanishingPointCluster] | None = None
    selected_cluster_id: int | None = None
    second_best_cluster_id: int | None = None
    cluster_ambiguity: float | None = None
    line_support_consistency: float | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "perspective_line_count": len(self.perspective_lines),
            "candidate_count": len(self.candidate_points),
            "confidence": self.confidence,
            "reason": self.reason,
            "selected_vanishing_point": (
                self.selected_vanishing_point.to_dict()
                if self.selected_vanishing_point is not None
                else None
            ),
            "clusters": [cluster.to_dict() for cluster in self.clusters or []],
            "selected_cluster_id": self.selected_cluster_id,
            "second_best_cluster_id": self.second_best_cluster_id,
            "cluster_ambiguity": self.cluster_ambiguity,
            "line_support_consistency": self.line_support_consistency,
        }
