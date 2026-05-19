from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.pose_estimation.domain.roll_estimate import RollEstimate
from src.contexts.pose_estimation.services.roll_estimator import candidate_lines
from src.contexts.preprocessing.domain.edge_map import EdgeMap
from src.contexts.preprocessing.domain.preprocessed_frame import PreprocessedFrame


def write_preprocessing_debug(
    debug_dir: Path,
    frame: PreprocessedFrame,
    edge_map: EdgeMap,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "input": debug_dir / "01_input.png",
        "grayscale": debug_dir / "02_grayscale.png",
        "blurred": debug_dir / "03_blurred.png",
        "edges": debug_dir / "04_edges.png",
    }
    cv2.imwrite(str(paths["input"]), frame.image_bgr)
    cv2.imwrite(str(paths["grayscale"]), frame.grayscale)
    cv2.imwrite(str(paths["blurred"]), frame.blurred)
    cv2.imwrite(str(paths["edges"]), edge_map.edges)
    return _string_paths(paths)


def write_line_debug(
    debug_dir: Path,
    frame: PreprocessedFrame,
    feature_set: LineFeatureSet,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    detected = _draw_lines(frame.image_bgr, feature_set.detected_lines, (180, 180, 180))
    filtered = _draw_lines(frame.image_bgr, feature_set.filtered_lines, (0, 255, 255))
    orientation = frame.image_bgr.copy()
    for line in feature_set.filtered_lines:
        color = _orientation_color(line.orientation)
        cv2.line(orientation, (line.x1, line.y1), (line.x2, line.y2), color, 2)

    paths = {
        "detected_lines": debug_dir / "05_detected_lines.png",
        "lines": debug_dir / "06_filtered_lines.png",
        "line_orientation_debug": debug_dir / "07_line_orientation_debug.png",
    }
    cv2.imwrite(str(paths["detected_lines"]), detected)
    cv2.imwrite(str(paths["lines"]), filtered)
    cv2.imwrite(str(paths["line_orientation_debug"]), orientation)
    return _string_paths(paths)


def write_roll_debug(
    debug_dir: Path,
    frame: PreprocessedFrame,
    feature_set: LineFeatureSet,
    roll_estimate: RollEstimate,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    candidates = candidate_lines(feature_set)
    candidate_image = _draw_lines(frame.image_bgr, candidates, (0, 200, 255))
    histogram = _orientation_histogram(candidates)
    overlay = candidate_image.copy()
    label = f"roll: {roll_estimate.roll if roll_estimate.roll is not None else 'N/A'} deg  conf: {roll_estimate.confidence:.2f}"
    cv2.putText(overlay, label, (24, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

    paths = {
        "roll_candidate_lines": debug_dir / "08_roll_candidate_lines.png",
        "roll_orientation_histogram": debug_dir / "09_roll_orientation_histogram.png",
        "roll_overlay": debug_dir / "10_roll_overlay.png",
    }
    cv2.imwrite(str(paths["roll_candidate_lines"]), candidate_image)
    cv2.imwrite(str(paths["roll_orientation_histogram"]), histogram)
    cv2.imwrite(str(paths["roll_overlay"]), overlay)
    return _string_paths(paths)


def _draw_lines(image: np.ndarray, lines: list[LineSegment], color: tuple[int, int, int]) -> np.ndarray:
    output = image.copy()
    for line in lines:
        cv2.line(output, (line.x1, line.y1), (line.x2, line.y2), color, 2)
    return output


def _orientation_color(orientation: str) -> tuple[int, int, int]:
    if orientation == "near_horizontal":
        return (0, 255, 0)
    if orientation == "near_vertical":
        return (255, 0, 0)
    return (0, 165, 255)


def _orientation_histogram(lines: list[LineSegment]) -> np.ndarray:
    canvas = np.full((240, 420, 3), 255, dtype=np.uint8)
    if not lines:
        cv2.putText(canvas, "No roll candidate lines", (36, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
        return canvas

    bins = list(range(-20, 22, 2))
    counts = [0.0 for _ in range(len(bins) - 1)]
    for line in lines:
        angle = line.angle_deg
        if line.orientation == "near_vertical":
            angle = angle - 90.0 if angle >= 0 else angle + 90.0
        for index in range(len(bins) - 1):
            if bins[index] <= angle < bins[index + 1]:
                counts[index] += line.length
                break

    max_count = max(counts) if counts else 0
    if max_count <= 0:
        return canvas

    chart_bottom = 210
    for index, count in enumerate(counts):
        x1 = 20 + index * 18
        x2 = x1 + 12
        height = int((count / max_count) * 170)
        cv2.rectangle(canvas, (x1, chart_bottom - height), (x2, chart_bottom), (80, 120, 220), -1)
    cv2.line(canvas, (20, chart_bottom), (400, chart_bottom), (0, 0, 0), 1)
    cv2.putText(canvas, "Roll orientation histogram", (55, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    return canvas


def _string_paths(paths: dict[str, Path]) -> dict[str, str]:
    return {key: str(path) for key, path in paths.items()}

