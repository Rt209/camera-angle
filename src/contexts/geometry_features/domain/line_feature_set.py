from __future__ import annotations

from dataclasses import dataclass

from src.contexts.geometry_features.domain.line_segment import LineSegment


@dataclass(frozen=True)
class LineFeatureSet:
    detected_lines: list[LineSegment]
    filtered_lines: list[LineSegment]

    @property
    def near_horizontal_lines(self) -> list[LineSegment]:
        return [line for line in self.filtered_lines if line.orientation == "near_horizontal"]

    @property
    def near_vertical_lines(self) -> list[LineSegment]:
        return [line for line in self.filtered_lines if line.orientation == "near_vertical"]

    def to_dict(self) -> dict[str, object]:
        return {
            "detected_line_count": len(self.detected_lines),
            "filtered_line_count": len(self.filtered_lines),
            "near_horizontal_count": len(self.near_horizontal_lines),
            "near_vertical_count": len(self.near_vertical_lines),
            "lines": [line.to_dict() for line in self.filtered_lines],
        }

