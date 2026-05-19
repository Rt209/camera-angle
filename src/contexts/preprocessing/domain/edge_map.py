from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EdgeMap:
    edges: np.ndarray
    width: int
    height: int

