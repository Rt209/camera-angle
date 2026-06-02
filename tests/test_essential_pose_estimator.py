from __future__ import annotations

import numpy as np

from src.contexts.pose_estimation.services.essential_pose_estimator import (
    ApproximateIntrinsics,
    EssentialPoseEstimator,
    UNCALIBRATED_WARNINGS,
)


def test_approximate_intrinsics_policy_uses_debug_default_k() -> None:
    intrinsics = ApproximateIntrinsics.from_image_size(1242, 374)

    assert intrinsics.camera_matrix.tolist() == [
        [1242.0, 0.0, 621.0],
        [0.0, 1242.0, 187.0],
        [0.0, 0.0, 1.0],
    ]
    assert intrinsics.warnings == UNCALIBRATED_WARNINGS


def test_essential_pose_estimator_warns_for_too_few_points() -> None:
    intrinsics = ApproximateIntrinsics.from_image_size(640, 480)
    points1 = np.array([[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]], dtype=np.float64)
    points2 = points1 + 1.0

    result = EssentialPoseEstimator().estimate(
        points1,
        points2,
        intrinsics.camera_matrix,
        frame_index=1,
        timestamp_sec=0.1,
        base_warnings=intrinsics.warnings,
    )

    assert result.inlier_count == 0
    assert result.confidence == 0.0
    assert "too_few_correspondences" in result.warnings
    assert "intrinsics_not_calibrated" in result.warnings

