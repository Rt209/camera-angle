from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from src.app.optical_flow_pose_overlay_pipeline import (
    UncalibratedPoseOverlayConfig,
    UncalibratedPoseOverlayPipeline,
)
from src.contexts.motion_analysis.services.sparse_flow_tracker import ShiTomasiConfig, SparseFlowTrackerConfig


def _write_grid_motion_video(path: Path, frame_count: int = 10) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (180, 120))
    assert writer.isOpened()
    try:
        for frame_index in range(frame_count):
            frame = np.zeros((120, 180, 3), dtype=np.uint8)
            for y in range(18, 105, 24):
                for x in range(18, 165, 24):
                    cv2.circle(frame, (x + frame_index * 2, y + frame_index), 4, (255, 255, 255), -1)
            writer.write(frame)
    finally:
        writer.release()


def test_uncalibrated_pose_overlay_pipeline_outputs_video_and_pose_rows(tmp_path: Path) -> None:
    video_path = tmp_path / "grid_motion.avi"
    debug_dir = tmp_path / "debug"
    _write_grid_motion_video(video_path)
    pipeline = UncalibratedPoseOverlayPipeline(
        UncalibratedPoseOverlayConfig(
            sparse_flow=SparseFlowTrackerConfig(
                feature=ShiTomasiConfig(max_corners=200, quality_level=0.01, min_distance=4),
                max_debug_frames=8,
                min_valid_tracks=4,
                redetect_below=4,
            ),
            output_debug_every_n_frames=2,
        )
    )

    result = pipeline.run(video_path, debug_dir)
    payload = json.loads(Path(result.frame_pose_results_json).read_text(encoding="utf-8"))

    assert Path(result.output_video).exists()
    assert Path(result.pose_timeline_csv).exists()
    assert Path(result.frame_pose_results_json).exists()
    assert len(result.pose_rows) > 0
    assert payload["calibrated_pose_result"] is False
    assert "intrinsics_not_calibrated" in payload["warnings"]
    assert all("intrinsics_not_calibrated" in frame["warnings"] for frame in payload["frames"])
    assert all("approximate_K_used" in frame["warnings"] for frame in payload["frames"])

