from __future__ import annotations

from dataclasses import dataclass

from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.geometry_features.domain.vanishing_point import VanishingPoint


@dataclass(frozen=True)
class VanishingPointFeatureSet:
    perspective_lines: list[LineSegment]
    candidate_points: list[tuple[float, float]]
    selected_vanishing_point: VanishingPoint | None
    confidence: float
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
        }
