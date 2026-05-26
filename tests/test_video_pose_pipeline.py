from pathlib import Path

import pytest

from src.app.video_pipeline import run_video_pose_pipeline
from src.contexts.input.adapters.video_source import FrameSamplingConfig


def test_video_pose_pipeline_end_to_end_smoke_on_kitti_no_overlay(tmp_path: Path) -> None:
    video_path = Path("tools/output/kitti_no_overlay.mp4")
    if not video_path.exists():
        pytest.skip("KITTI no-overlay test video is not available.")

    result = run_video_pose_pipeline(
        video_path,
        tmp_path / "video_pose",
        sampling_config=FrameSamplingConfig(sample_every=50),
        write_overlay=True,
        debug_sampled_frames=False,
    )

    assert result.csv_path.exists()
    assert result.json_path.exists()
    assert result.overlay_path is not None
    assert result.overlay_path.exists()
    assert len(result.frame_results) > 0
    assert "debug_artifacts" not in result.frame_results[0].pose_result or not result.frame_results[0].pose_result["debug_artifacts"]
