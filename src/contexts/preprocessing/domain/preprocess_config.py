from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessConfig:
    max_width: int = 1280
    blur_kernel_size: int = 5
    canny_threshold1: int = 50
    canny_threshold2: int = 150

