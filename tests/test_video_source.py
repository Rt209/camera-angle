from pathlib import Path

import cv2
import numpy as np
import pytest

from src.contexts.input.adapters.video_source import FrameSamplingConfig, VideoSource
from src.shared.errors import VideoSourceError


def _write_test_video(path: Path, frame_count: int = 5, fps: float = 10.0) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 48))
    assert writer.isOpened()
    try:
        for index in range(frame_count):
            frame = np.full((48, 64, 3), 30 + index * 20, dtype=np.uint8)
            cv2.line(frame, (5, 24), (58, 24), (255, 255, 255), 2)
            writer.write(frame)
    finally:
        writer.release()


def test_video_source_reads_metadata_and_sampled_frames(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    _write_test_video(video_path, frame_count=6, fps=12.0)

    source = VideoSource(video_path)
    sampled = list(source.iter_sampled_frames(FrameSamplingConfig(sample_every=2)))

    assert source.metadata.frame_count == 6
    assert source.metadata.width == 64
    assert source.metadata.height == 48
    assert sampled[0].frame_index == 0
    assert [frame.frame_index for frame in sampled] == [0, 2, 4]
    assert sampled[0].frame.metadata["source"] == "video"
    assert sampled[0].frame.image_bgr.shape == (48, 64, 3)


def test_video_source_missing_path_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(VideoSourceError, match="does not exist"):
        VideoSource(tmp_path / "missing.mp4")


def test_video_source_rejects_unopenable_video(tmp_path: Path) -> None:
    bad_video = tmp_path / "not_video.mp4"
    bad_video.write_text("not a real mp4", encoding="utf-8")

    with pytest.raises(VideoSourceError, match="Could not open video"):
        VideoSource(bad_video)


def test_sampling_config_uses_target_fps() -> None:
    assert FrameSamplingConfig(sample_every=1, target_fps=5.0).step_for_source_fps(20.0) == 4
