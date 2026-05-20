from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VanishingPoint:
    x: float
    y: float
    confidence: float
    support_count: int
    spread: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

