from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PreprocessedFrame:
    image_bgr: np.ndarray
    grayscale: np.ndarray
    blurred: np.ndarray
    scale: float
    width: int
    height: int

