from __future__ import annotations

from dataclasses import dataclass

from src.contexts.geometry_features.domain.horizon_line import HorizonLine
from src.contexts.geometry_features.domain.line_segment import LineSegment


@dataclass(frozen=True)
class HorizonFeatureSet:
    candidates: list[LineSegment]
    selected_horizon: HorizonLine | None
    confidence: float
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_count": len(self.candidates),
            "confidence": self.confidence,
            "reason": self.reason,
            "selected_horizon": (
                self.selected_horizon.to_dict() if self.selected_horizon is not None else None
            ),
        }

