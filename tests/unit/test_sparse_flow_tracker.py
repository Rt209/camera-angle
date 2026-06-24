from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.motion_analysis.services.sparse_flow_tracker import (
    ShiTomasiConfig,
    SparseFlowTracker,
    SparseFlowTrackerConfig,
)


def _write_moving_squares_video(path: Path, frame_count: int = 8, shift_per_frame: tuple[int, int] = (3, 2)) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (160, 120))
    assert writer.isOpened()
    base_positions = [(20, 20), (68, 24), (112, 42), (38, 78), (96, 86)]
    try:
        for frame_index in range(frame_count):
            frame = np.zeros((120, 160, 3), dtype=np.uint8)
            dx = shift_per_frame[0] * frame_index
            dy = shift_per_frame[1] * frame_index
            for x, y in base_positions:
                cv2.rectangle(frame, (x + dx, y + dy), (x + dx + 14, y + dy + 14), (255, 255, 255), -1)
            writer.write(frame)
    finally:
        writer.release()


def _write_blank_video(path: Path, frame_count: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (80, 60))
    assert writer.isOpened()
    try:
        for _ in range(frame_count):
            writer.write(np.zeros((60, 80, 3), dtype=np.uint8))
    finally:
        writer.release()


def test_sparse_flow_tracker_tracks_synthetic_moving_features(tmp_path: Path) -> None:
    video_path = tmp_path / "moving_squares.avi"
    _write_moving_squares_video(video_path)
    tracker = SparseFlowTracker(
        SparseFlowTrackerConfig(
            feature=ShiTomasiConfig(max_corners=100, quality_level=0.01, min_distance=4),
            max_processing_frames=8,
            write_debug_frames=True,
            max_debug_frames=8,
            output_debug_every_n_frames=2,
            min_valid_tracks=4,
            redetect_below=4,
        )
    )

    result = tracker.track_video(video_path)

    assert result.processed_frame_count == 8
    assert len(result.frame_summaries) == 7
    assert len(result.flow_vectors) > 0
    assert result.aggregate_summary()["mean_valid_track_count"] >= 4
    assert 2.0 <= result.aggregate_summary()["mean_flow_magnitude"] <= 5.0
    assert result.frame_summaries[0].tracked_point_count > 0
    assert result.frame_summaries[0].valid_track_count > 0
    assert result.to_summary_dict()["calibration_required"] is False
    assert result.to_summary_dict()["pose_estimation_performed"] is False


def test_flow_statistics_include_expected_fields(tmp_path: Path) -> None:
    video_path = tmp_path / "moving_squares.avi"
    _write_moving_squares_video(video_path)
    result = SparseFlowTracker(SparseFlowTrackerConfig(max_processing_frames=3, min_valid_tracks=1)).track_video(video_path)

    frame_payload = result.to_summary_dict()["frames"][0]

    assert set(frame_payload) == {
        "frame_index",
        "timestamp_sec",
        "tracked_point_count",
        "valid_track_count",
        "mean_flow_magnitude",
        "median_flow_magnitude",
        "max_flow_magnitude",
        "dominant_direction_deg",
        "warnings",
    }
    assert frame_payload["max_flow_magnitude"] >= frame_payload["median_flow_magnitude"]


def test_sparse_flow_tracker_warns_when_features_are_too_few(tmp_path: Path) -> None:
    video_path = tmp_path / "blank.avi"
    _write_blank_video(video_path)

    result = SparseFlowTracker(SparseFlowTrackerConfig(max_processing_frames=4, min_valid_tracks=2)).track_video(video_path)

    assert "too_few_feature_points" in result.warnings
    assert all(summary.valid_track_count == 0 for summary in result.frame_summaries)


def test_debug_limit_does_not_limit_processing_and_debug_is_opt_in(tmp_path: Path) -> None:
    video_path = tmp_path / "moving_squares.avi"
    _write_moving_squares_video(video_path, frame_count=8)

    normal = SparseFlowTracker(
        SparseFlowTrackerConfig(max_debug_frames=1, min_valid_tracks=1)
    ).track_video(video_path)
    assert normal.processed_frame_count == 8
    assert len(normal.frame_summaries) == 7
    assert normal.debug_frames == []

    debug = SparseFlowTracker(
        SparseFlowTrackerConfig(
            write_debug_frames=True,
            max_debug_frames=2,
            output_debug_every_n_frames=2,
            min_valid_tracks=1,
        )
    ).track_video(video_path)
    assert debug.processed_frame_count == 8
    assert [frame.frame_index for frame in debug.debug_frames] == [2, 4]
