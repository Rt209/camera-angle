from __future__ import annotations

import cv2

from src.contexts.input.domain.frame import Frame
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig
from src.contexts.preprocessing.domain.preprocessed_frame import PreprocessedFrame


def preprocess_frame(frame: Frame, config: PreprocessConfig) -> PreprocessedFrame:
    image = frame.image_bgr
    scale = 1.0
    if frame.width > config.max_width:
        scale = config.max_width / frame.width
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kernel = config.blur_kernel_size
    if kernel % 2 == 0:
        kernel += 1
    blurred = cv2.GaussianBlur(grayscale, (kernel, kernel), 0)
    height, width = image.shape[:2]
    return PreprocessedFrame(
        image_bgr=image,
        grayscale=grayscale,
        blurred=blurred,
        scale=scale,
        width=width,
        height=height,
    )

