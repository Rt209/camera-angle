from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VanishingPointCluster:
    cluster_id: int
    center_x: float
    center_y: float
    support_count: int
    spread: float
    score: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)
