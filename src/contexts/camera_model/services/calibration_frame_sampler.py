from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from src.contexts.input.adapters.video_source import FrameSamplingConfig, SampledVideoFrame, VideoSource


@dataclass(frozen=True)
class CalibrationFrameSamplerConfig:
    frame_step: int = 5
    max_frames: int | None = 80


class CalibrationFrameSampler:
    def sample(self, video_path: Path, config: CalibrationFrameSamplerConfig) -> Iterator[SampledVideoFrame]:
        count = 0
        source = VideoSource(video_path)
        for sampled in source.iter_sampled_frames(FrameSamplingConfig(sample_every=config.frame_step)):
            yield sampled
            count += 1
            if config.max_frames is not None and count >= config.max_frames:
                break

