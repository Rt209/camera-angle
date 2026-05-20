from __future__ import annotations

from math import atan, degrees

from src.contexts.geometry_features.domain.vanishing_point_feature_set import VanishingPointFeatureSet
from src.contexts.pose_estimation.domain.yaw_estimate import YawEstimate


def estimate_yaw(
    vanishing_point_features: VanishingPointFeatureSet,
    image_width: int,
    image_height: int | None = None,
    focal_length_pixels: float | None = None,
) -> YawEstimate:
    vanishing_point = vanishing_point_features.selected_vanishing_point
    if vanishing_point is None:
        return YawEstimate(
            yaw=None,
            confidence=0.0,
            unit="degree",
            method="vanishing_point_based_yaw_estimation",
            reason=vanishing_point_features.reason or "vanishing_point_unavailable",
        )

    focal_reference = min(image_width, image_height) if image_height is not None else image_width
    focal_length = focal_length_pixels or focal_reference / 2.0
    center_x = image_width / 2.0
    yaw = degrees(atan((vanishing_point.x - center_x) / max(focal_length, 1.0)))
    return YawEstimate(
        yaw=round(yaw, 2),
        confidence=vanishing_point.confidence,
        unit="degree",
        method="vanishing_point_based_yaw_estimation",
    )
