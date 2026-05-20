from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HorizonLine:
    x1: int
    y1: int
    x2: int
    y2: int
    angle_deg: float
    y_at_center: float
    confidence: float
    support_count: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

