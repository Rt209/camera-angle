from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RollEstimate:
    roll: float | None
    confidence: float
    unit: str
    method: str
    candidate_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

