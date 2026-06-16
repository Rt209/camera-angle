from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from src.app.pipeline import PoseIntegrationPipelineResult, run_stage_4_7_pose_pipeline_on_frame
from src.contexts.input.adapters.video_source import FrameSamplingConfig, VideoMetadata, VideoSource
from src.contexts.pose_estimation.services.yaw_reliability_gate import apply_video_yaw_reliability
from src.contexts.output.services.video_pose_writer import (
    write_frame_results_json,
    write_pose_timeline_csv,
    write_predicted_overlay_video,
)


@dataclass(frozen=True)
class VideoPoseFrameResult:
    frame_index: int
    time_sec: float
    status: str
    frame_bgr: np.ndarray | None
    pose_result: dict[str, Any]
    feature_metadata: dict[str, Any]
    warnings: list[str]
    failure_reason: str | None = None

    @classmethod
    def from_pipeline_result(
        cls,
        frame_index: int,
        time_sec: float,
        pipeline_result: PoseIntegrationPipelineResult,
    ) -> "VideoPoseFrameResult":
        pose = pipeline_result.pose_result.to_dict()
        values = [pose.get("yaw"), pose.get("pitch"), pose.get("roll")]
        if all(value is not None for value in values):
            status = "full"
        elif any(value is not None for value in values):
            status = "partial"
        else:
            status = "failed"

        feature_metadata = _feature_metadata(pipeline_result)
        return cls(
            frame_index=frame_index,
            time_sec=time_sec,
            status=status,
            frame_bgr=pipeline_result.frame.image_bgr,
            pose_result=pose,
            feature_metadata=feature_metadata,
            warnings=list(pose.get("warnings") or []),
        )

    @classmethod
    def failed(
        cls,
        frame_index: int,
        time_sec: float,
        frame_bgr: np.ndarray | None,
        reason: str,
    ) -> "VideoPoseFrameResult":
        return cls(
            frame_index=frame_index,
            time_sec=time_sec,
            status="failed",
            frame_bgr=frame_bgr,
            pose_result={
                "yaw": None,
                "pitch": None,
                "roll": None,
                "confidence": 0.0,
                "angle_confidence": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            },
            feature_metadata={},
            warnings=[reason],
            failure_reason=reason,
        )

    def to_timeline_row(self) -> dict[str, Any]:
        yaw = self.pose_result.get("yaw")
        pitch = self.pose_result.get("pitch")
        roll = self.pose_result.get("roll")
        angle_confidence = self.pose_result.get("angle_confidence") or {}
        yaw_reliability = self.feature_metadata.get("yaw_reliability") or {}
        return {
            "frame_index": self.frame_index,
            "time_sec": round(self.time_sec, 6),
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "raw_yaw": yaw_reliability.get("raw_vp_yaw", yaw),
            "raw_pitch": pitch,
            "raw_roll": roll,
            "smoothed_yaw": None,
            "smoothed_pitch": None,
            "smoothed_roll": None,
            "confidence": self.pose_result.get("confidence"),
            "yaw_confidence": angle_confidence.get("yaw"),
            "pitch_confidence": angle_confidence.get("pitch"),
            "roll_confidence": angle_confidence.get("roll"),
            "status": self.status,
            "warnings": self.warnings,
            **_timeline_feature_columns(self.feature_metadata),
            **_timeline_yaw_reliability_columns(yaw_reliability),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "time_sec": self.time_sec,
            "status": self.status,
            "pose_result": self.pose_result,
            "feature_metadata": self.feature_metadata,
            "warnings": self.warnings,
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True)
class VideoPosePipelineResult:
    video_metadata: VideoMetadata
    sampling_config: FrameSamplingConfig
    frame_results: list[VideoPoseFrameResult]
    csv_path: Path
    json_path: Path
    overlay_path: Path | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_metadata": self.video_metadata.to_dict(),
            "sampling_config": self.sampling_config.to_dict(),
            "csv_path": str(self.csv_path),
            "json_path": str(self.json_path),
            "overlay_path": str(self.overlay_path) if self.overlay_path is not None else None,
            "sampled_frame_count": len(self.frame_results),
        }


def run_video_pose_pipeline(
    video_path: Path,
    output_dir: Path,
    sampling_config: FrameSamplingConfig,
    write_overlay: bool = False,
    debug_sampled_frames: bool = False,
) -> VideoPosePipelineResult:
    source = VideoSource(video_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_root = output_dir / "debug_frames"
    frame_results: list[VideoPoseFrameResult] = []

    for sampled in source.iter_sampled_frames(sampling_config):
        try:
            frame_debug_dir = debug_root / f"frame_{sampled.frame_index:06d}"
            pipeline_result = run_stage_4_7_pose_pipeline_on_frame(sampled.frame, frame_debug_dir)
            frame_results.append(
                VideoPoseFrameResult.from_pipeline_result(
                    sampled.frame_index,
                    sampled.time_sec,
                    pipeline_result,
                )
            )
        except Exception as exc:
            frame_results.append(
                VideoPoseFrameResult.failed(
                    sampled.frame_index,
                    sampled.time_sec,
                    sampled.frame.image_bgr,
                    f"{type(exc).__name__}: {exc}",
                )
            )

    apply_video_yaw_reliability(frame_results, source.metadata.width)

    if not debug_sampled_frames and debug_root.exists():
        _remove_debug_artifacts_from_results(frame_results)
        shutil.rmtree(debug_root)

    csv_path = output_dir / "pose_timeline.csv"
    json_path = output_dir / "frame_pose_results.json"
    write_pose_timeline_csv(frame_results, csv_path)
    write_frame_results_json(
        frame_results,
        json_path,
        video_metadata=source.metadata.to_dict(),
        sampling_config=sampling_config.to_dict(),
    )

    overlay_path = None
    if write_overlay:
        overlay_path = output_dir / "predicted_pose_overlay.mp4"
        output_fps = _output_fps(source.metadata.fps, sampling_config)
        write_predicted_overlay_video(
            frame_results,
            overlay_path,
            fps=output_fps,
            size=(source.metadata.width, source.metadata.height),
        )

    return VideoPosePipelineResult(
        video_metadata=source.metadata,
        sampling_config=sampling_config,
        frame_results=frame_results,
        csv_path=csv_path,
        json_path=json_path,
        overlay_path=overlay_path,
    )


def _feature_metadata(result: PoseIntegrationPipelineResult) -> dict[str, Any]:
    line_data = result.line_features.to_dict()
    horizon_data = result.horizon_features.to_dict()
    vp_data = result.vanishing_point_features.to_dict()
    return {
        "line_features": {
            "detected_line_count": line_data["detected_line_count"],
            "filtered_line_count": line_data["filtered_line_count"],
            "near_horizontal_count": line_data["near_horizontal_count"],
            "near_vertical_count": line_data["near_vertical_count"],
        },
        "horizon_features": horizon_data,
        "vanishing_point_features": vp_data,
    }


def _timeline_feature_columns(feature_metadata: dict[str, Any]) -> dict[str, Any]:
    line = feature_metadata.get("line_features") or {}
    horizon = feature_metadata.get("horizon_features") or {}
    vp = feature_metadata.get("vanishing_point_features") or {}
    selected_horizon = horizon.get("selected_horizon") or {}
    selected_vp = vp.get("selected_vanishing_point") or {}
    return {
        "detected_line_count": line.get("detected_line_count"),
        "near_horizontal_count": line.get("near_horizontal_count"),
        "near_vertical_count": line.get("near_vertical_count"),
        "perspective_line_count": vp.get("perspective_line_count"),
        "vanishing_point_candidate_count": vp.get("candidate_count"),
        "horizon_candidate_count": horizon.get("candidate_count"),
        "selected_horizon_y_at_center": selected_horizon.get("y_at_center"),
        "selected_vanishing_point_x": selected_vp.get("x"),
        "selected_vanishing_point_y": selected_vp.get("y"),
        "selected_cluster_id": vp.get("selected_cluster_id"),
        "second_best_cluster_id": vp.get("second_best_cluster_id"),
    }


def _timeline_yaw_reliability_columns(yaw_reliability: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_vp_yaw": yaw_reliability.get("raw_vp_yaw"),
        "image_geometry_yaw": yaw_reliability.get("image_geometry_yaw"),
        "calibrated_heading_yaw": yaw_reliability.get("calibrated_heading_yaw"),
        "comparison_ready": yaw_reliability.get("comparison_ready"),
        "pose_semantics": yaw_reliability.get("pose_semantics"),
        "vp_temporal_jump": yaw_reliability.get("vp_temporal_jump"),
        "vp_side_flip": yaw_reliability.get("vp_side_flip"),
        "vp_cluster_ambiguity": yaw_reliability.get("vp_cluster_ambiguity"),
        "line_support_consistency": yaw_reliability.get("line_support_consistency"),
        "yaw_warning_flags": yaw_reliability.get("yaw_warning_flags"),
    }


def _output_fps(source_fps: float, sampling_config: FrameSamplingConfig) -> float:
    if sampling_config.target_fps is not None:
        return sampling_config.target_fps
    step = sampling_config.step_for_source_fps(source_fps)
    return max(source_fps / step, 1.0) if source_fps > 0 else 1.0


def _remove_debug_artifacts_from_results(frame_results: list[VideoPoseFrameResult]) -> None:
    for result in frame_results:
        result.pose_result.get("debug_artifacts", {}).clear()
