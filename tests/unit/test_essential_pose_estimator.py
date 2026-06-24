from __future__ import annotations

import numpy as np
import cv2

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
    assert result.status == "failed"
    assert result.raw_yaw_deg is None


def test_multiple_essential_candidates_selects_most_pose_inliers(monkeypatch) -> None:
    candidates = np.vstack([np.eye(3), np.eye(3) * 2.0])
    monkeypatch.setattr(cv2, "findEssentialMat", lambda *args, **kwargs: (candidates, np.ones((8, 1), np.uint8)))

    def recover(candidate, *args, **kwargs):
        recovered = 3 if candidate[0, 0] == 1.0 else 8
        return recovered, np.eye(3), np.array([[1.0], [0.0], [0.0]]), np.ones((8, 1), np.uint8)

    monkeypatch.setattr(cv2, "recoverPose", recover)
    points = np.column_stack([np.arange(8, dtype=float) * 10, np.arange(8, dtype=float) * 5])
    result = EssentialPoseEstimator().estimate(points, points + [2.0, 0.0], np.eye(3), 1, 0.1)

    assert result.essential_candidate_count == 2
    assert result.selected_candidate_index == 1
    assert result.inlier_count == 8


def test_low_parallax_is_rejected_but_raw_rotation_is_preserved(monkeypatch) -> None:
    monkeypatch.setattr(cv2, "findEssentialMat", lambda *args, **kwargs: (np.eye(3), np.ones((8, 1), np.uint8)))
    monkeypatch.setattr(
        cv2, "recoverPose",
        lambda *args, **kwargs: (8, np.eye(3), np.array([[1.0], [0.0], [0.0]]), np.ones((8, 1), np.uint8)),
    )
    points = np.column_stack([np.arange(8, dtype=float) * 10, np.arange(8, dtype=float) * 5])
    result = EssentialPoseEstimator().estimate(points, points + 0.01, np.eye(3), 1, 0.1)

    assert result.status == "rejected"
    assert result.rejection_reason == "low_parallax_degeneracy"
    assert result.yaw_deg is None
    assert result.raw_yaw_deg == 0.0
