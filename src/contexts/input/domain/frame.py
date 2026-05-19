from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Frame:
    path: Path
    image_bgr: np.ndarray
    width: int
    height: int
    metadata: dict[str, Any]

    @property
    def filename(self) -> str:
        return self.path.name

