from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class YawEstimate:
    yaw: float | None
    confidence: float
    unit: str
    method: str
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

