from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2

from src.contexts.input.domain.frame import Frame
from src.contexts.input.services.image_loader import frame_from_bgr
from src.shared.errors import VideoSourceError


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    fps: float
    frame_count: int
    width: int
    height: int
    duration_sec: float

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "width": self.width,
            "height": self.height,
            "duration_sec": self.duration_sec,
        }


@dataclass(frozen=True)
class SampledVideoFrame:
    frame_index: int
    time_sec: float
    frame: Frame


@dataclass(frozen=True)
class FrameSamplingConfig:
    sample_every: int = 1
    target_fps: float | None = None

    def step_for_source_fps(self, source_fps: float) -> int:
        if self.target_fps is not None:
            if self.target_fps <= 0:
                raise VideoSourceError("target_fps must be greater than zero.")
            if source_fps <= 0:
                raise VideoSourceError("Cannot use target_fps because source FPS is unavailable.")
            return max(1, round(source_fps / self.target_fps))
        if self.sample_every < 1:
            raise VideoSourceError("sample_every must be at least 1.")
        return self.sample_every

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_every": self.sample_every,
            "target_fps": self.target_fps,
        }


class VideoSource:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise VideoSourceError(f"Video path does not exist: {self.path}")
        if not self.path.is_file():
            raise VideoSourceError(f"Video path is not a file: {self.path}")

        capture = cv2.VideoCapture(str(self.path))
        try:
            if not capture.isOpened():
                raise VideoSourceError(f"Could not open video: {self.path}")

            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            if frame_count <= 0 or width <= 0 or height <= 0:
                raise VideoSourceError(f"Video has no readable frames or invalid metadata: {self.path}")

            duration = frame_count / fps if fps > 0 else 0.0
            self.metadata = VideoMetadata(
                path=str(self.path),
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
                duration_sec=duration,
            )
        finally:
            capture.release()

    def iter_sampled_frames(self, config: FrameSamplingConfig) -> Iterator[SampledVideoFrame]:
        step = config.step_for_source_fps(self.metadata.fps)
        capture = cv2.VideoCapture(str(self.path))
        try:
            if not capture.isOpened():
                raise VideoSourceError(f"Could not open video: {self.path}")

            frame_index = 0
            while True:
                ok, image_bgr = capture.read()
                if not ok:
                    break
                if frame_index % step == 0:
                    time_sec = frame_index / self.metadata.fps if self.metadata.fps > 0 else 0.0
                    frame = frame_from_bgr(
                        image_bgr,
                        name=f"frame_{frame_index:06d}.png",
                        metadata={
                            "source": "video",
                            "video_path": str(self.path),
                            "frame_index": frame_index,
                            "time_sec": time_sec,
                        },
                    )
                    yield SampledVideoFrame(frame_index=frame_index, time_sec=time_sec, frame=frame)
                frame_index += 1
        finally:
            capture.release()
