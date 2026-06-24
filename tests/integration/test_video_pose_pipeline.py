from pathlib import Path

import pytest

from src.app.video_pipeline import run_video_pose_pipeline
from src.contexts.input.adapters.video_source import FrameSamplingConfig
from unittest.mock import patch
from src.cli.parser import build_parser


def test_video_pose_pipeline_end_to_end_smoke_on_kitti_no_overlay(tmp_path: Path) -> None:
    video_path = Path("data/samples/kitti/videos/kitti_no_overlay.mp4")
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
    assert result.overlay_path.name == "pose_overlay.mp4"
    assert len(result.frame_results) > 0
    assert "debug_artifacts" not in result.frame_results[0].pose_result or not result.frame_results[0].pose_result["debug_artifacts"]
    assert not (tmp_path / "video_pose" / "debug_frames").exists()


def test_geometry_debug_disabled_never_calls_imwrite(tmp_path: Path) -> None:
    video_path = Path("data/samples/kitti/videos/kitti_no_overlay.mp4")
    with patch("src.contexts.output.services.debug_visualizer.cv2.imwrite") as imwrite:
        run_video_pose_pipeline(
            video_path,
            tmp_path / "video_pose",
            sampling_config=FrameSamplingConfig(sample_every=100),
            debug_sampled_frames=False,
        )
    imwrite.assert_not_called()


def test_single_image_cli_debug_is_opt_in() -> None:
    args = build_parser().parse_args(["--path", "image.png"])
    assert args.debug_dir is None
