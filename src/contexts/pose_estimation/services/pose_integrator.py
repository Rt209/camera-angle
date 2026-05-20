from __future__ import annotations

from src.contexts.pose_estimation.domain.pitch_estimate import PitchEstimate
from src.contexts.pose_estimation.domain.pose_result import PoseResult
from src.contexts.pose_estimation.domain.roll_estimate import RollEstimate
from src.contexts.pose_estimation.domain.yaw_estimate import YawEstimate
from src.contexts.pose_estimation.services.pose_confidence import angle_confidence, overall_confidence


def build_pose_result(
    image: str,
    yaw: YawEstimate,
    pitch: PitchEstimate,
    roll: RollEstimate,
    stage: str,
    debug_artifacts: dict[str, str] | None = None,
    warnings: list[str] | None = None,
) -> PoseResult:
    confidence_by_angle = angle_confidence(yaw, pitch, roll)
    features_used = ["edges", "lines"]
    if roll.roll is not None:
        features_used.append("vertical_lines")
    if pitch.pitch is not None:
        features_used.append("horizon")
    if yaw.yaw is not None:
        features_used.append("vanishing_point")

    method = "geometry_based_pose_estimation"
    if yaw.yaw is None or pitch.pitch is None or roll.roll is None:
        method = "geometry_based_partial_pose_estimation"

    return PoseResult(
        image=image,
        yaw=yaw.yaw,
        pitch=pitch.pitch,
        roll=roll.roll,
        unit="degree",
        confidence=overall_confidence(confidence_by_angle),
        method=method,
        stage=stage,
        features_used=features_used,
        angle_confidence=confidence_by_angle,
        debug_artifacts=debug_artifacts or {},
        warnings=warnings or [],
    )
