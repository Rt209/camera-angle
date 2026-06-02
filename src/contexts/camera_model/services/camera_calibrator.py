from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.contexts.camera_model.domain.calibration_result import CalibrationResult
from src.contexts.camera_model.domain.intrinsics import CameraIntrinsics
from src.contexts.camera_model.services.calibration_board_detector import (
    CalibrationBoardConfig,
    CalibrationBoardDetector,
)
from src.contexts.camera_model.services.calibration_frame_sampler import (
    CalibrationFrameSampler,
    CalibrationFrameSamplerConfig,
)


@dataclass(frozen=True)
class CameraCalibrationConfig:
    board: CalibrationBoardConfig = CalibrationBoardConfig()
    sampler: CalibrationFrameSamplerConfig = CalibrationFrameSamplerConfig()
    min_valid_frames: int = 8
    source_label: str = "calibration_video"


class CameraCalibrator:
    def __init__(
        self,
        config: CameraCalibrationConfig,
        detector: CalibrationBoardDetector | None = None,
        sampler: CalibrationFrameSampler | None = None,
    ) -> None:
        self.config = config
        self.detector = detector or CalibrationBoardDetector(config.board)
        self.sampler = sampler or CalibrationFrameSampler()

    def calibrate_from_video(self, video_path: Path, detected_corners_dir: Path | None = None) -> CalibrationResult:
        object_points: list[np.ndarray] = []
        image_points: list[np.ndarray] = []
        debug_images: list[str] = []
        image_size: tuple[int, int] | None = None
        attempted = 0

        if detected_corners_dir is not None:
            detected_corners_dir.mkdir(parents=True, exist_ok=True)

        for sampled in self.sampler.sample(video_path, self.config.sampler):
            attempted += 1
            frame = sampled.frame
            image_size = (frame.width, frame.height)
            detection = self.detector.detect(frame.image_bgr)
            if not detection.found or detection.object_points is None or detection.image_points is None:
                continue

            object_points.append(detection.object_points)
            image_points.append(detection.image_points)
            if detected_corners_dir is not None and detection.annotated_bgr is not None:
                debug_path = detected_corners_dir / f"frame_{sampled.frame_index:06d}_corners.png"
                cv2.imwrite(str(debug_path), detection.annotated_bgr)
                debug_images.append(str(debug_path))

        if image_size is None:
            raise RuntimeError("No frames were sampled from the calibration video.")
        return self.calibrate_from_points(
            object_points=object_points,
            image_points=image_points,
            image_size=image_size,
            attempted_frame_count=attempted,
            debug_images=debug_images,
        )

    def calibrate_from_points(
        self,
        object_points: list[np.ndarray],
        image_points: list[np.ndarray],
        image_size: tuple[int, int],
        attempted_frame_count: int | None = None,
        debug_images: list[str] | None = None,
    ) -> CalibrationResult:
        if len(object_points) < self.config.min_valid_frames:
            raise RuntimeError(
                f"Need at least {self.config.min_valid_frames} valid calibration frames; got {len(object_points)}."
            )

        rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            object_points,
            image_points,
            image_size,
            None,
            None,
        )
        mean_error = self._mean_reprojection_error(object_points, image_points, rvecs, tvecs, camera_matrix, dist_coeffs)
        warnings: list[str] = []
        if mean_error > 1.0:
            warnings.append("high_reprojection_error")

        intrinsics = CameraIntrinsics(
            camera_matrix=camera_matrix,
            dist_coeffs=dist_coeffs,
            image_width=image_size[0],
            image_height=image_size[1],
        )
        return CalibrationResult(
            intrinsics=intrinsics,
            reprojection_error=float(mean_error if np.isfinite(mean_error) else rms),
            calibration_pattern=self.config.board.pattern,
            calibration_frame_count=len(object_points),
            attempted_frame_count=attempted_frame_count if attempted_frame_count is not None else len(object_points),
            source=self.config.source_label,
            board_rows=self.config.board.board_rows,
            board_cols=self.config.board.board_cols,
            square_size=self.config.board.square_size,
            debug_images=debug_images or [],
            warnings=warnings,
        )

    def write_outputs(self, result: CalibrationResult, output_json: Path, report_path: Path) -> None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        report_path.write_text(self.render_report(result, output_json), encoding="utf-8")

    def render_report(self, result: CalibrationResult, output_json: Path | None = None) -> str:
        data = result.to_dict()
        lines = [
            "# Camera Calibration Report",
            "",
            "Phase 1 - Camera Calibration From Video",
            "",
            f"- Source: {result.source}",
            f"- Pattern: {result.calibration_pattern}",
            f"- Board inner corners: {result.board_cols} x {result.board_rows}",
            f"- Square size: {result.square_size}",
            f"- Valid frames: {result.calibration_frame_count} / {result.attempted_frame_count}",
            f"- Image size: {result.intrinsics.image_width} x {result.intrinsics.image_height}",
            f"- Reprojection error: {result.reprojection_error:.6f} px",
            f"- fx/fy/cx/cy: {result.intrinsics.fx:.3f}, {result.intrinsics.fy:.3f}, "
            f"{result.intrinsics.cx:.3f}, {result.intrinsics.cy:.3f}",
            f"- Output JSON: {output_json}" if output_json is not None else "- Output JSON: not written",
            f"- Debug corner images: {len(result.debug_images)}",
            "",
            "## Notes",
            "",
        ]
        if "synthetic" in result.source:
            lines.append("- This run uses synthetic / fixture calibration data because no real calibration video is available.")
        else:
            lines.append("- Intrinsics were estimated from calibration video frames using cv2.calibrateCamera.")
        if result.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in result.warnings)
        lines.extend(["", "## camera_intrinsics.json Fields", ""])
        lines.extend(f"- {key}" for key in data.keys())
        return "\n".join(lines) + "\n"

    @staticmethod
    def _mean_reprojection_error(
        object_points: list[np.ndarray],
        image_points: list[np.ndarray],
        rvecs: tuple[np.ndarray, ...],
        tvecs: tuple[np.ndarray, ...],
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> float:
        total_error = 0.0
        total_points = 0
        for obj, img, rvec, tvec in zip(object_points, image_points, rvecs, tvecs):
            projected, _ = cv2.projectPoints(obj, rvec, tvec, camera_matrix, dist_coeffs)
            projected = projected.reshape(-1, 2)
            err = cv2.norm(img.reshape(-1, 2), projected, cv2.NORM_L2)
            total_error += err * err
            total_points += len(obj)
        return float(np.sqrt(total_error / total_points)) if total_points else float("nan")

