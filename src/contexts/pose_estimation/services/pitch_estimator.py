from __future__ import annotations

from math import atan, degrees

from src.contexts.geometry_features.domain.horizon_feature_set import HorizonFeatureSet
from src.contexts.pose_estimation.domain.pitch_estimate import PitchEstimate


def estimate_pitch(
    horizon_features: HorizonFeatureSet,
    image_width: int,
    image_height: int,
    focal_length_pixels: float | None = None,
    principal_point_y: float | None = None,
) -> PitchEstimate:
    horizon = horizon_features.selected_horizon
    if horizon is None:
        return PitchEstimate(
            pitch=None,
            confidence=0.0,
            unit="degree",
            method="horizon_based_pitch_estimation",
            reason=horizon_features.reason or "horizon_unavailable",
        )

    focal_length = focal_length_pixels or image_width / 2.0
    center_y = image_height / 2.0 if principal_point_y is None else principal_point_y
    pitch = degrees(atan((center_y - horizon.y_at_center) / max(focal_length, 1.0)))
    return PitchEstimate(
        pitch=round(pitch, 2),
        confidence=horizon.confidence,
        unit="degree",
        method="horizon_based_pitch_estimation",
    )
