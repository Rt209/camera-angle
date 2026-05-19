from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.input.domain.frame import Frame
from src.io.image_loader import open_image
from src.shared.errors import ImageLoadError


def load_frame(path: Path) -> Frame:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        image = _load_with_pillow(path)

    if image is None:
        raise ImageLoadError(f"Could not load image pixels: {path}")

    height, width = image.shape[:2]
    return Frame(
        path=path,
        image_bgr=image,
        width=width,
        height=height,
        metadata={"source": "image", "extension": path.suffix.lower()},
    )


def _load_with_pillow(path: Path) -> np.ndarray | None:
    try:
        with open_image(path) as image:
            rgb = np.asarray(image.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        return None

