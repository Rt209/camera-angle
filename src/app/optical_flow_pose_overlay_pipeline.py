from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np

from src.contexts.motion_analysis.domain.flow_track import SparseFlowResult
from src.contexts.camera_model.domain.intrinsics import load_camera_intrinsics
from src.contexts.camera_model.services.kitti_calibration_loader import load_kitti_calibration
from src.contexts.motion_analysis.services.sparse_flow_tracker import SparseFlowTracker, SparseFlowTrackerConfig
from src.contexts.output.services.optical_flow_pose_visualizer import (
    draw_uncalibrated_pose_overlay,
    write_overlay_debug_frame,
)
from src.contexts.pose_estimation.services.essential_pose_estimator import (
    ApproximateIntrinsics,
    EssentialPoseEstimator,
    RelativePoseEstimate,
)
from src.shared.errors import VideoOutputError
from src.shared.output_contract import DEBUG_DIRECTORY, FRAME_RESULTS, OVERLAY_VIDEO, POSE_TIMELINE, pose_metadata


@dataclass(frozen=True)
class UncalibratedPoseOverlayConfig:
    sparse_flow: SparseFlowTrackerConfig = SparseFlowTrackerConfig()
    write_debug_frames: bool = False
    debug_every_n_frames: int = 10
    max_debug_frames: int = 120
    camera_intrinsics_path: Path | None = None
    kitti_calibration_directory: Path | None = None
    kitti_camera_index: str = "03"
    max_temporal_rotation_deg: float = 30.0


@dataclass(frozen=True)
class UncalibratedPoseOverlayResult:
    output_video: str
    pose_timeline_csv: str
    frame_pose_results_json: str
    debug_frames: list[str]
    pose_rows: list[RelativePoseEstimate]
    intrinsics: ApproximateIntrinsics
    sparse_flow: SparseFlowResult

    def summary(self) -> dict[str, object]:
        ratios = [row.inlier_ratio for row in self.pose_rows]
        confidences = [row.confidence for row in self.pose_rows]
        return {
            "pose_frame_count": len(self.pose_rows),
            "mean_inlier_ratio": float(np.mean(ratios)) if ratios else 0.0,
            "mean_confidence": float(np.mean(confidences)) if confidences else 0.0,
            "warnings": list(self.intrinsics.warnings),
            "intrinsics_source": self.intrinsics.source,
            "intrinsics_calibrated": not self.intrinsics.warnings,
        }


class UncalibratedPoseOverlayPipeline:
    def __init__(self, config: UncalibratedPoseOverlayConfig | None = None) -> None:
        self.config = config or UncalibratedPoseOverlayConfig()
        self.estimator = EssentialPoseEstimator()

    def run(self, video_path: Path, debug_dir: Path) -> UncalibratedPoseOverlayResult:
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_video = debug_dir / OVERLAY_VIDEO
        timeline_csv = debug_dir / POSE_TIMELINE
        results_json = debug_dir / FRAME_RESULTS
        debug_frame_dir = debug_dir / DEBUG_DIRECTORY

        sparse_flow = SparseFlowTracker(self.config.sparse_flow).track_video(video_path)
        intrinsics = self._resolve_intrinsics(
            sparse_flow.image_width, sparse_flow.image_height
        )
        pose_rows = self._estimate_pose_rows(sparse_flow, intrinsics)
        debug_frames = self._write_overlay_video(video_path, output_video, debug_frame_dir, sparse_flow, pose_rows)
        self._write_timeline_csv(timeline_csv, pose_rows, sparse_flow.fps, self.config.sparse_flow.frame_step)
        self._write_results_json(
            results_json,
            pose_rows,
            intrinsics,
            sparse_flow,
            output_video,
            debug_frames,
            self.config.sparse_flow.frame_step,
        )
        return UncalibratedPoseOverlayResult(
            output_video=str(output_video),
            pose_timeline_csv=str(timeline_csv),
            frame_pose_results_json=str(results_json),
            debug_frames=debug_frames,
            pose_rows=pose_rows,
            intrinsics=intrinsics,
            sparse_flow=sparse_flow,
        )

    def _resolve_intrinsics(self, video_width: int, video_height: int) -> ApproximateIntrinsics:
        if (
            self.config.camera_intrinsics_path is not None
            and self.config.kitti_calibration_directory is not None
        ):
            raise ValueError(
                "Use either camera_intrinsics_path or kitti_calibration_directory, not both."
            )
        if self.config.kitti_calibration_directory is not None:
            profile = load_kitti_calibration(
                self.config.kitti_calibration_directory,
                self.config.kitti_camera_index,
            )
            loaded = profile.intrinsics
            source = f"kitti_P_rect_{profile.camera_index}"
        elif self.config.camera_intrinsics_path is not None:
            loaded = load_camera_intrinsics(self.config.camera_intrinsics_path)
            source = "calibrated_file"
        else:
            return ApproximateIntrinsics.from_image_size(video_width, video_height)

        scaled = loaded.camera_matrix_for_size(video_width, video_height)
        return ApproximateIntrinsics(scaled, [], source)

    def _estimate_pose_rows(
        self,
        sparse_flow: SparseFlowResult,
        intrinsics: ApproximateIntrinsics,
    ) -> list[RelativePoseEstimate]:
        rows = []
        previous_accepted_rotation: np.ndarray | None = None
        estimator = self.estimator
        if not intrinsics.warnings:
            estimator = EssentialPoseEstimator(
                replace(self.estimator.config, intrinsics_quality=1.0)
            )
        for summary in sparse_flow.frame_summaries:
            vectors = [vector for vector in sparse_flow.flow_vectors if vector.frame_index == summary.frame_index]
            prev_points = np.asarray([(vector.x0, vector.y0) for vector in vectors], dtype=np.float64)
            curr_points = np.asarray([(vector.x1, vector.y1) for vector in vectors], dtype=np.float64)
            estimate = estimator.estimate(
                    previous_points=prev_points,
                    current_points=curr_points,
                    camera_matrix=intrinsics.camera_matrix,
                    frame_index=summary.frame_index,
                    timestamp_sec=summary.timestamp_sec,
                    base_warnings=list(intrinsics.warnings),
                )
            if estimate.rotation_matrix is not None and estimate.status == "accepted":
                rotation = np.asarray(estimate.rotation_matrix, dtype=np.float64)
                if previous_accepted_rotation is not None:
                    delta = previous_accepted_rotation.T @ rotation
                    cosine = np.clip((np.trace(delta) - 1.0) / 2.0, -1.0, 1.0)
                    change_deg = float(np.degrees(np.arccos(cosine)))
                    if change_deg > self.config.max_temporal_rotation_deg:
                        estimate = replace(
                            estimate, yaw_deg=None, pitch_deg=None, roll_deg=None,
                            status="rejected", rejection_reason="temporal_rotation_jump",
                            warnings=sorted(set(estimate.warnings + ["temporal_rotation_jump"])),
                        )
                if estimate.status == "accepted":
                    previous_accepted_rotation = rotation
            rows.append(estimate)
        return rows

    def _write_overlay_video(
        self,
        video_path: Path,
        output_video: Path,
        debug_frame_dir: Path,
        sparse_flow: SparseFlowResult,
        pose_rows: list[RelativePoseEstimate],
    ) -> list[str]:
        pose_by_frame = {row.frame_index: row for row in pose_rows}
        vectors_by_frame: dict[int, list] = {}
        for vector in sparse_flow.flow_vectors:
            vectors_by_frame.setdefault(vector.frame_index, []).append(vector)

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise VideoOutputError(f"Could not open video for overlay: {video_path}")
        writer = cv2.VideoWriter(
            str(output_video),
            cv2.VideoWriter_fourcc(*"mp4v"),
            sparse_flow.fps if sparse_flow.fps > 0 else 10.0,
            (sparse_flow.image_width, sparse_flow.image_height),
        )
        if not writer.isOpened():
            capture.release()
            raise VideoOutputError(f"Could not open output video writer: {output_video}")

        debug_paths: list[str] = []
        try:
            frame_index = 0
            while frame_index < sparse_flow.processed_frame_count:
                ok, frame = capture.read()
                if not ok:
                    break
                pose = pose_by_frame.get(frame_index)
                overlay = draw_uncalibrated_pose_overlay(frame, vectors_by_frame.get(frame_index, []), pose)
                writer.write(overlay)
                if (
                    self.config.write_debug_frames
                    and len(debug_paths) < self.config.max_debug_frames
                    and frame_index > 0
                    and frame_index % max(1, self.config.debug_every_n_frames) == 0
                ):
                    debug_paths.append(write_overlay_debug_frame(debug_frame_dir, frame_index, overlay))
                frame_index += 1
        finally:
            capture.release()
            writer.release()
        return debug_paths

    @staticmethod
    def _write_timeline_csv(
        path: Path,
        pose_rows: list[RelativePoseEstimate],
        fps: float,
        frame_step: int,
    ) -> None:
        fieldnames = [
            "schema_version",
            "pipeline",
            "pose_type",
            "sample_index",
            "source_frame_index_prev",
            "source_frame_index_curr",
            "timestamp_sec_prev",
            "timestamp_sec_curr",
            "yaw_deg",
            "pitch_deg",
            "roll_deg",
            "raw_yaw_deg",
            "raw_pitch_deg",
            "raw_roll_deg",
            "unit",
            "rotation_order",
            "intrinsics_source",
            "tracked_point_count",
            "inlier_count",
            "inlier_ratio",
            "confidence",
            "status",
            "rejection_reason",
            "essential_candidate_count",
            "selected_candidate_index",
            "warnings",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample_index, row in enumerate(pose_rows):
                payload = _optical_frame_payload(row, sample_index, fps, frame_step)
                payload["warnings"] = "|".join(row.warnings)
                writer.writerow({key: payload.get(key) for key in fieldnames})

    @staticmethod
    def _write_results_json(
        path: Path,
        pose_rows: list[RelativePoseEstimate],
        intrinsics: ApproximateIntrinsics,
        sparse_flow: SparseFlowResult,
        output_video: Path,
        debug_frames: list[str],
        frame_step: int,
    ) -> None:
        intrinsics_calibrated = not intrinsics.warnings
        pipeline_warnings = list(intrinsics.warnings)
        payload = {
            **pose_metadata(
                "optical",
                intrinsics_calibrated=intrinsics_calibrated,
                intrinsics_source=intrinsics.source,
            ),
            "source": {
                "input_path": sparse_flow.video_path,
                "fps": sparse_flow.fps,
                "frame_count": sparse_flow.processed_frame_count,
            },
            "sampling": {"sample_every": frame_step},
            "stage": (
                "calibrated_relative_pose_overlay"
                if intrinsics_calibrated
                else "uncalibrated_pose_overlay_prototype"
            ),
            "calibrated_pose_result": intrinsics_calibrated,
            "warnings": pipeline_warnings,
            "intrinsics": intrinsics.to_dict(),
            "output_video": str(output_video),
            "debug_frames": debug_frames,
            "sparse_flow_summary": sparse_flow.aggregate_summary(),
            "frames": [
                _optical_frame_payload(row, sample_index, sparse_flow.fps, frame_step)
                for sample_index, row in enumerate(pose_rows)
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _optical_frame_payload(
    row: RelativePoseEstimate,
    sample_index: int,
    fps: float,
    frame_step: int,
) -> dict[str, object]:
    current = row.frame_index
    previous = max(0, current - frame_step)
    valid = row.yaw_deg is not None and row.pitch_deg is not None and row.roll_deg is not None
    return {
        **pose_metadata(
            "optical",
            intrinsics_calibrated=("intrinsics_not_calibrated" not in row.warnings),
            intrinsics_source=(
                "calibrated_file"
                if "intrinsics_not_calibrated" not in row.warnings
                else "approximate_from_image_size"
            ),
        ),
        **row.to_dict(),
        "sample_index": sample_index,
        "source_frame_index_prev": previous,
        "source_frame_index_curr": current,
        "timestamp_sec_prev": previous / fps if fps > 0 else 0.0,
        "timestamp_sec_curr": row.timestamp_sec,
        "unit": "degree",
        "rotation_order": "ZYX",
        "intrinsics_source": "calibrated_file" if not row.warnings or "intrinsics_not_calibrated" not in row.warnings else "approximate_from_image_size",
        "status": row.status if row.status else ("accepted" if valid else "failed"),
    }
