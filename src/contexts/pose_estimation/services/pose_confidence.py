from __future__ import annotations

from src.contexts.pose_estimation.domain.pitch_estimate import PitchEstimate
from src.contexts.pose_estimation.domain.roll_estimate import RollEstimate
from src.contexts.pose_estimation.domain.yaw_estimate import YawEstimate


def angle_confidence(
    yaw: YawEstimate,
    pitch: PitchEstimate,
    roll: RollEstimate,
) -> dict[str, float]:
    return {
        "yaw": yaw.confidence,
        "pitch": pitch.confidence,
        "roll": roll.confidence,
    }


def overall_confidence(confidence_by_angle: dict[str, float]) -> float:
    valid = [value for value in confidence_by_angle.values() if value > 0]
    if not valid:
        return 0.0
    return round(sum(valid) / len(valid), 2)

