from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PoseResult:
    image: str
    yaw: float | None
    pitch: float | None
    roll: float | None
    unit: str
    confidence: float
    method: str
    stage: str
    features_used: list[str]
    debug_artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "image": self.image,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "roll": self.roll,
            "unit": self.unit,
            "confidence": self.confidence,
            "method": self.method,
            "stage": self.stage,
            "features_used": self.features_used,
            "debug_artifacts": self.debug_artifacts,
            "warnings": self.warnings,
        }

