from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.contexts.motion_analysis.domain.flow_track import SparseFlowResult
from src.contexts.motion_analysis.services.sparse_flow_tracker import SparseFlowTracker, SparseFlowTrackerConfig
from src.contexts.output.services.optical_flow_pose_visualizer import (
    draw_uncalibrated_pose_overlay,
    write_overlay_debug_frame,
)
from src.contexts.pose_estimation.services.essential_pose_estimator import (
    ApproximateIntrinsics,
    EssentialPoseEstimator,
    RelativePoseEstimate,
    UNCALIBRATED_WARNINGS,
)
from src.shared.errors import VideoOutputError


@dataclass(frozen=True)
class UncalibratedPoseOverlayConfig:
    sparse_flow: SparseFlowTrackerConfig = SparseFlowTrackerConfig()
    output_debug_every_n_frames: int = 10


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
            "warnings": list(UNCALIBRATED_WARNINGS),
        }


class UncalibratedPoseOverlayPipeline:
    def __init__(self, config: UncalibratedPoseOverlayConfig | None = None) -> None:
        self.config = config or UncalibratedPoseOverlayConfig()
        self.estimator = EssentialPoseEstimator()

    def run(self, video_path: Path, debug_dir: Path) -> UncalibratedPoseOverlayResult:
        debug_dir.mkdir(parents=True, exist_ok=True)
        output_video = debug_dir / "output_pose_overlay.mp4"
        timeline_csv = debug_dir / "pose_timeline.csv"
        results_json = debug_dir / "frame_pose_results.json"
        debug_frame_dir = debug_dir / "debug_frames"

        sparse_flow = SparseFlowTracker(self.config.sparse_flow).track_video(video_path)
        intrinsics = ApproximateIntrinsics.from_image_size(sparse_flow.image_width, sparse_flow.image_height)
        pose_rows = self._estimate_pose_rows(sparse_flow, intrinsics)
        debug_frames = self._write_overlay_video(video_path, output_video, debug_frame_dir, sparse_flow, pose_rows)
        self._write_timeline_csv(timeline_csv, pose_rows)
        self._write_results_json(results_json, pose_rows, intrinsics, sparse_flow, output_video, debug_frames)
        return UncalibratedPoseOverlayResult(
            output_video=str(output_video),
            pose_timeline_csv=str(timeline_csv),
            frame_pose_results_json=str(results_json),
            debug_frames=debug_frames,
            pose_rows=pose_rows,
            intrinsics=intrinsics,
            sparse_flow=sparse_flow,
        )

    def _estimate_pose_rows(
        self,
        sparse_flow: SparseFlowResult,
        intrinsics: ApproximateIntrinsics,
    ) -> list[RelativePoseEstimate]:
        rows = []
        for summary in sparse_flow.frame_summaries:
            vectors = [vector for vector in sparse_flow.flow_vectors if vector.frame_index == summary.frame_index]
            prev_points = np.asarray([(vector.x0, vector.y0) for vector in vectors], dtype=np.float64)
            curr_points = np.asarray([(vector.x1, vector.y1) for vector in vectors], dtype=np.float64)
            rows.append(
                self.estimator.estimate(
                    previous_points=prev_points,
                    current_points=curr_points,
                    camera_matrix=intrinsics.camera_matrix,
                    frame_index=summary.frame_index,
                    timestamp_sec=summary.timestamp_sec,
                    base_warnings=list(intrinsics.warnings),
                )
            )
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
                if frame_index > 0 and frame_index % max(1, self.config.output_debug_every_n_frames) == 0:
                    debug_paths.append(write_overlay_debug_frame(debug_frame_dir, frame_index, overlay))
                frame_index += 1
        finally:
            capture.release()
            writer.release()
        return debug_paths

    @staticmethod
    def _write_timeline_csv(path: Path, pose_rows: list[RelativePoseEstimate]) -> None:
        fieldnames = [
            "frame_index",
            "timestamp_sec",
            "yaw_deg",
            "pitch_deg",
            "roll_deg",
            "tracked_point_count",
            "inlier_count",
            "inlier_ratio",
            "confidence",
            "warnings",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in pose_rows:
                payload = row.to_dict()
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
    ) -> None:
        payload = {
            "stage": "uncalibrated_pose_overlay_prototype",
            "calibrated_pose_result": False,
            "warnings": list(UNCALIBRATED_WARNINGS),
            "intrinsics": intrinsics.to_dict(),
            "output_video": str(output_video),
            "debug_frames": debug_frames,
            "sparse_flow_summary": sparse_flow.aggregate_summary(),
            "frames": [row.to_dict() for row in pose_rows],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

