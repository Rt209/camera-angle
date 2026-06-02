from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FlowVector:
    track_id: int
    frame_index: int
    timestamp_sec: float
    x0: float
    y0: float
    x1: float
    y1: float
    dx: float
    dy: float
    magnitude: float
    direction_deg: float
    lk_error: float | None = None

    def to_csv_row(self) -> dict[str, object]:
        return {
            "track_id": self.track_id,
            "frame_index": self.frame_index,
            "timestamp_sec": self.timestamp_sec,
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "dx": self.dx,
            "dy": self.dy,
            "magnitude": self.magnitude,
            "direction_deg": self.direction_deg,
            "lk_error": self.lk_error,
        }


@dataclass(frozen=True)
class FlowFrameSummary:
    frame_index: int
    timestamp_sec: float
    tracked_point_count: int
    valid_track_count: int
    mean_flow_magnitude: float
    median_flow_magnitude: float
    max_flow_magnitude: float
    dominant_direction_deg: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_index": self.frame_index,
            "timestamp_sec": self.timestamp_sec,
            "tracked_point_count": self.tracked_point_count,
            "valid_track_count": self.valid_track_count,
            "mean_flow_magnitude": self.mean_flow_magnitude,
            "median_flow_magnitude": self.median_flow_magnitude,
            "max_flow_magnitude": self.max_flow_magnitude,
            "dominant_direction_deg": self.dominant_direction_deg,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class FlowDebugFrame:
    frame_index: int
    timestamp_sec: float
    image_bgr: object
    flow_vectors: list[FlowVector]
    paths: dict[int, list[tuple[float, float]]]
    summary: FlowFrameSummary


@dataclass(frozen=True)
class SparseFlowResult:
    video_path: str
    fps: float
    image_width: int
    image_height: int
    processed_frame_count: int
    frame_summaries: list[FlowFrameSummary]
    flow_vectors: list[FlowVector]
    debug_frames: list[FlowDebugFrame]
    warnings: list[str] = field(default_factory=list)

    def aggregate_summary(self) -> dict[str, object]:
        valid_counts = [summary.valid_track_count for summary in self.frame_summaries]
        mean_magnitudes = [summary.mean_flow_magnitude for summary in self.frame_summaries]
        median_magnitudes = [summary.median_flow_magnitude for summary in self.frame_summaries]
        return {
            "video_path": self.video_path,
            "fps": self.fps,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "processed_frame_count": self.processed_frame_count,
            "summary_frame_count": len(self.frame_summaries),
            "total_flow_vector_count": len(self.flow_vectors),
            "mean_valid_track_count": sum(valid_counts) / len(valid_counts) if valid_counts else 0.0,
            "mean_flow_magnitude": sum(mean_magnitudes) / len(mean_magnitudes) if mean_magnitudes else 0.0,
            "mean_median_flow_magnitude": sum(median_magnitudes) / len(median_magnitudes) if median_magnitudes else 0.0,
            "warnings": self.warnings,
        }

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "stage": "sparse_optical_flow_tracking",
            "calibration_required": False,
            "pose_estimation_performed": False,
            "aggregate": self.aggregate_summary(),
            "frames": [summary.to_dict() for summary in self.frame_summaries],
        }

