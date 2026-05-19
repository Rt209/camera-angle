from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan2, degrees, hypot


@dataclass(frozen=True)
class LineSegment:
    x1: int
    y1: int
    x2: int
    y2: int
    length: float
    angle_deg: float
    orientation: str

    @classmethod
    def from_points(
        cls,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        horizontal_threshold_deg: float,
        vertical_threshold_deg: float,
    ) -> "LineSegment":
        dx = x2 - x1
        dy = y2 - y1
        length = hypot(dx, dy)
        angle = _normalize_angle(degrees(atan2(dy, dx)))
        orientation = classify_orientation(angle, horizontal_threshold_deg, vertical_threshold_deg)
        return cls(x1=x1, y1=y1, x2=x2, y2=y2, length=length, angle_deg=angle, orientation=orientation)

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def classify_orientation(
    angle_deg: float,
    horizontal_threshold_deg: float,
    vertical_threshold_deg: float,
) -> str:
    if abs(angle_deg) <= horizontal_threshold_deg:
        return "near_horizontal"
    if abs(abs(angle_deg) - 90.0) <= vertical_threshold_deg:
        return "near_vertical"
    return "diagonal"


def _normalize_angle(angle_deg: float) -> float:
    while angle_deg >= 90.0:
        angle_deg -= 180.0
    while angle_deg < -90.0:
        angle_deg += 180.0
    return angle_deg

