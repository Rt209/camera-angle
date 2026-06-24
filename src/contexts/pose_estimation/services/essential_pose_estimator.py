from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from src.contexts.pose_estimation.services.euler_angle_converter import EulerAngles, rotation_matrix_to_euler_zyx

UNCALIBRATED_WARNINGS = ["intrinsics_not_calibrated", "approximate_K_used", "pose_for_debug_only"]


@dataclass(frozen=True)
class ApproximateIntrinsics:
    camera_matrix: np.ndarray
    warnings: list[str]
    source: str = "approximate_from_image_size"

    @classmethod
    def from_image_size(cls, width: int, height: int) -> "ApproximateIntrinsics":
        focal = float(max(width, height))
        return cls(
            camera_matrix=np.array(
                [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]],
                dtype=np.float64,
            ),
            warnings=list(UNCALIBRATED_WARNINGS),
        )

    def to_dict(self) -> dict[str, object]:
        return {"camera_matrix": self.camera_matrix.tolist(), "warnings": self.warnings, "source": self.source}


@dataclass(frozen=True)
class RelativePoseEstimate:
    frame_index: int
    timestamp_sec: float
    tracked_point_count: int
    inlier_count: int
    inlier_ratio: float
    confidence: float
    yaw_deg: float | None
    pitch_deg: float | None
    roll_deg: float | None
    rotation_matrix: list[list[float]] | None
    translation_direction: list[float] | None
    inlier_mask: list[bool]
    warnings: list[str] = field(default_factory=list)
    raw_yaw_deg: float | None = None
    raw_pitch_deg: float | None = None
    raw_roll_deg: float | None = None
    status: str = "accepted"
    rejection_reason: str | None = None
    essential_candidate_count: int = 0
    selected_candidate_index: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_index": self.frame_index,
            "timestamp_sec": self.timestamp_sec,
            "tracked_point_count": self.tracked_point_count,
            "inlier_count": self.inlier_count,
            "inlier_ratio": self.inlier_ratio,
            "confidence": self.confidence,
            "yaw_deg": self.yaw_deg,
            "pitch_deg": self.pitch_deg,
            "roll_deg": self.roll_deg,
            "rotation_matrix": self.rotation_matrix,
            "translation_direction": self.translation_direction,
            "inlier_mask": self.inlier_mask,
            "warnings": self.warnings,
            "raw_yaw_deg": self.raw_yaw_deg,
            "raw_pitch_deg": self.raw_pitch_deg,
            "raw_roll_deg": self.raw_roll_deg,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "essential_candidate_count": self.essential_candidate_count,
            "selected_candidate_index": self.selected_candidate_index,
        }


@dataclass(frozen=True)
class EssentialPoseEstimatorConfig:
    ransac_threshold: float = 1.0
    ransac_probability: float = 0.999
    min_points: int = 8
    intrinsics_quality: float = 0.4
    min_median_parallax_px: float = 0.25


class EssentialPoseEstimator:
    def __init__(self, config: EssentialPoseEstimatorConfig | None = None) -> None:
        self.config = config or EssentialPoseEstimatorConfig()

    def estimate(
        self,
        previous_points: np.ndarray,
        current_points: np.ndarray,
        camera_matrix: np.ndarray,
        frame_index: int,
        timestamp_sec: float,
        base_warnings: list[str] | None = None,
    ) -> RelativePoseEstimate:
        points1 = np.asarray(previous_points, dtype=np.float64).reshape(-1, 2)
        points2 = np.asarray(current_points, dtype=np.float64).reshape(-1, 2)
        tracked_count = min(len(points1), len(points2))
        warnings = list(base_warnings or [])

        if tracked_count < self.config.min_points:
            warnings.append("too_few_correspondences")
            return self._empty(frame_index, timestamp_sec, tracked_count, warnings)

        essential, mask = cv2.findEssentialMat(
            points1,
            points2,
            camera_matrix,
            method=cv2.RANSAC,
            prob=self.config.ransac_probability,
            threshold=self.config.ransac_threshold,
        )
        if essential is None or mask is None:
            warnings.append("essential_matrix_failed")
            return self._empty(frame_index, timestamp_sec, tracked_count, warnings)

        mask_u8 = mask.astype(np.uint8).reshape(-1, 1)
        candidates = [essential[index:index + 3, :3] for index in range(0, essential.shape[0], 3)]
        solutions = []
        for index, candidate in enumerate(candidates):
            recovered, rotation, translation, pose_mask = cv2.recoverPose(
                candidate, points1, points2, camera_matrix, mask=mask_u8.copy()
            )
            solutions.append((int(recovered), index, rotation, translation, pose_mask))
        recovered, selected_index, rotation, translation, pose_mask = max(solutions, key=lambda item: item[0])
        pose_mask_bool = (pose_mask.reshape(-1) > 0).tolist() if pose_mask is not None else (mask.reshape(-1) > 0).tolist()
        inlier_count = int(recovered)
        inlier_ratio = inlier_count / tracked_count if tracked_count else 0.0
        if inlier_count < self.config.min_points:
            warnings.append("too_few_pose_inliers")

        angles: EulerAngles = rotation_matrix_to_euler_zyx(rotation)
        median_parallax = float(np.median(np.linalg.norm(points2 - points1, axis=1)))
        rejected = median_parallax < self.config.min_median_parallax_px
        if rejected:
            warnings.append("low_parallax_degeneracy")
        tracking_quality = min(1.0, tracked_count / 100.0)
        pose_stability = min(1.0, inlier_ratio * 1.5)
        confidence = _clamp(inlier_ratio * tracking_quality * pose_stability * self.config.intrinsics_quality)
        return RelativePoseEstimate(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            tracked_point_count=tracked_count,
            inlier_count=inlier_count,
            inlier_ratio=inlier_ratio,
            confidence=confidence,
            yaw_deg=None if rejected else angles.yaw_deg,
            pitch_deg=None if rejected else angles.pitch_deg,
            roll_deg=None if rejected else angles.roll_deg,
            rotation_matrix=rotation.astype(float).tolist(),
            translation_direction=translation.reshape(-1).astype(float).tolist(),
            inlier_mask=pose_mask_bool,
            warnings=sorted(set(warnings)),
            raw_yaw_deg=angles.yaw_deg,
            raw_pitch_deg=angles.pitch_deg,
            raw_roll_deg=angles.roll_deg,
            status="rejected" if rejected else "accepted",
            rejection_reason="low_parallax_degeneracy" if rejected else None,
            essential_candidate_count=len(candidates),
            selected_candidate_index=selected_index,
        )

    @staticmethod
    def _empty(
        frame_index: int,
        timestamp_sec: float,
        tracked_count: int,
        warnings: list[str],
    ) -> RelativePoseEstimate:
        return RelativePoseEstimate(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            tracked_point_count=tracked_count,
            inlier_count=0,
            inlier_ratio=0.0,
            confidence=0.0,
            yaw_deg=None,
            pitch_deg=None,
            roll_deg=None,
            rotation_matrix=None,
            translation_direction=None,
            inlier_mask=[False] * tracked_count,
            warnings=sorted(set(warnings)),
            status="failed",
        )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
