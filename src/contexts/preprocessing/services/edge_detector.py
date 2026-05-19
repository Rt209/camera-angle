from __future__ import annotations

import cv2

from src.contexts.preprocessing.domain.edge_map import EdgeMap
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig
from src.contexts.preprocessing.domain.preprocessed_frame import PreprocessedFrame


def detect_edges(frame: PreprocessedFrame, config: PreprocessConfig) -> EdgeMap:
    edges = cv2.Canny(frame.blurred, config.canny_threshold1, config.canny_threshold2)
    height, width = edges.shape[:2]
    return EdgeMap(edges=edges, width=width, height=height)

