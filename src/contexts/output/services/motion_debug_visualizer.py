from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.motion_analysis.domain.flow_track import FlowDebugFrame, FlowVector


def write_sparse_flow_debug_frames(debug_dir: Path, debug_frames: list[FlowDebugFrame]) -> dict[str, list[str]]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    vector_paths: list[str] = []
    track_paths: list[str] = []
    for debug_frame in debug_frames:
        vectors = draw_flow_vectors(debug_frame.image_bgr, debug_frame.flow_vectors)
        paths = draw_tracked_paths(debug_frame.image_bgr, debug_frame.paths, debug_frame.flow_vectors)
        vector_path = debug_dir / f"flow_vectors_{debug_frame.frame_index:06d}.png"
        path_path = debug_dir / f"tracked_paths_{debug_frame.frame_index:06d}.png"
        cv2.imwrite(str(vector_path), vectors)
        cv2.imwrite(str(path_path), paths)
        vector_paths.append(str(vector_path))
        track_paths.append(str(path_path))
    return {"flow_vectors": vector_paths, "tracked_paths": track_paths}


def draw_flow_vectors(image_bgr: np.ndarray, vectors: list[FlowVector]) -> np.ndarray:
    output = image_bgr.copy()
    for vector in vectors:
        start = (int(round(vector.x0)), int(round(vector.y0)))
        end = (int(round(vector.x1)), int(round(vector.y1)))
        color = _magnitude_color(vector.magnitude)
        cv2.arrowedLine(output, start, end, color, 2, cv2.LINE_AA, tipLength=0.25)
        cv2.circle(output, end, 2, (255, 255, 255), -1, cv2.LINE_AA)
    _draw_label(output, f"sparse LK vectors: {len(vectors)}")
    return output


def draw_tracked_paths(
    image_bgr: np.ndarray,
    paths: dict[int, list[tuple[float, float]]],
    vectors: list[FlowVector],
) -> np.ndarray:
    output = image_bgr.copy()
    active_ids = {vector.track_id for vector in vectors}
    for track_id, points in paths.items():
        if len(points) < 2:
            continue
        color = (0, 220, 255) if track_id in active_ids else (120, 120, 120)
        rounded = [(int(round(x)), int(round(y))) for x, y in points]
        for start, end in zip(rounded[:-1], rounded[1:]):
            cv2.line(output, start, end, color, 1, cv2.LINE_AA)
        if track_id in active_ids:
            cv2.circle(output, rounded[-1], 2, (0, 255, 0), -1, cv2.LINE_AA)
    _draw_label(output, f"tracked paths: {len(paths)}")
    return output


def _magnitude_color(magnitude: float) -> tuple[int, int, int]:
    if magnitude < 1.0:
        return (255, 180, 0)
    if magnitude < 5.0:
        return (0, 220, 255)
    return (0, 80, 255)


def _draw_label(image: np.ndarray, text: str) -> None:
    cv2.putText(image, text, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(image, text, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

