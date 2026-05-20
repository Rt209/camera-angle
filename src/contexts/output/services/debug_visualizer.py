from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.geometry_features.domain.horizon_feature_set import HorizonFeatureSet
from src.contexts.geometry_features.domain.vanishing_point_feature_set import VanishingPointFeatureSet
from src.contexts.pose_estimation.domain.roll_estimate import RollEstimate
from src.contexts.pose_estimation.domain.pose_result import PoseResult
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


def write_horizon_debug(
    debug_dir: Path,
    frame: PreprocessedFrame,
    horizon_features: HorizonFeatureSet,
    pitch_value: float | None,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    candidates_image = _draw_lines(frame.image_bgr, horizon_features.candidates, (0, 200, 255))
    selected_image = frame.image_bgr.copy()
    if horizon_features.selected_horizon is not None:
        horizon = horizon_features.selected_horizon
        cv2.line(selected_image, (horizon.x1, horizon.y1), (horizon.x2, horizon.y2), (0, 255, 0), 3)
    overlay = selected_image.copy()
    center_y = frame.height // 2
    cv2.line(overlay, (0, center_y), (frame.width - 1, center_y), (255, 0, 0), 1)
    pitch_label = f"pitch: {pitch_value if pitch_value is not None else 'N/A'} deg"
    cv2.putText(overlay, pitch_label, (24, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2, cv2.LINE_AA)

    paths = {
        "horizon_candidates": debug_dir / "11_horizon_candidates.png",
        "horizon": debug_dir / "12_selected_horizon.png",
        "pitch_overlay": debug_dir / "13_pitch_overlay.png",
    }
    cv2.imwrite(str(paths["horizon_candidates"]), candidates_image)
    cv2.imwrite(str(paths["horizon"]), selected_image)
    cv2.imwrite(str(paths["pitch_overlay"]), overlay)
    return _string_paths(paths)


def write_vanishing_point_debug(
    debug_dir: Path,
    frame: PreprocessedFrame,
    vanishing_point_features: VanishingPointFeatureSet,
    yaw_value: float | None,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    perspective_image = _draw_lines(frame.image_bgr, vanishing_point_features.perspective_lines, (0, 165, 255))
    candidates_image = perspective_image.copy()
    for x, y in vanishing_point_features.candidate_points[:200]:
        if -frame.width <= x <= frame.width * 2 and -frame.height <= y <= frame.height * 2:
            cv2.circle(candidates_image, (int(round(x)), int(round(y))), 2, (255, 0, 255), -1)

    selected_image = perspective_image.copy()
    if vanishing_point_features.selected_vanishing_point is not None:
        point = vanishing_point_features.selected_vanishing_point
        _draw_cross(selected_image, int(round(point.x)), int(round(point.y)), (0, 255, 0))

    overlay = selected_image.copy()
    center_x = frame.width // 2
    cv2.line(overlay, (center_x, 0), (center_x, frame.height - 1), (255, 0, 0), 1)
    yaw_label = f"yaw: {yaw_value if yaw_value is not None else 'N/A'} deg"
    cv2.putText(overlay, yaw_label, (24, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2, cv2.LINE_AA)

    paths = {
        "perspective_lines": debug_dir / "14_perspective_lines.png",
        "vanishing_point_candidates": debug_dir / "15_vanishing_point_candidates.png",
        "vanishing_point": debug_dir / "16_selected_vanishing_point.png",
        "yaw_overlay": debug_dir / "17_yaw_overlay.png",
    }
    cv2.imwrite(str(paths["perspective_lines"]), perspective_image)
    cv2.imwrite(str(paths["vanishing_point_candidates"]), candidates_image)
    cv2.imwrite(str(paths["vanishing_point"]), selected_image)
    cv2.imwrite(str(paths["yaw_overlay"]), overlay)
    return _string_paths(paths)


def write_pose_overlay(
    debug_dir: Path,
    frame: PreprocessedFrame,
    horizon_features: HorizonFeatureSet,
    vanishing_point_features: VanishingPointFeatureSet,
    pose_result: PoseResult,
) -> dict[str, str]:
    debug_dir.mkdir(parents=True, exist_ok=True)
    overlay = frame.image_bgr.copy()
    if horizon_features.selected_horizon is not None:
        horizon = horizon_features.selected_horizon
        cv2.line(overlay, (horizon.x1, horizon.y1), (horizon.x2, horizon.y2), (0, 255, 0), 3)
    if vanishing_point_features.selected_vanishing_point is not None:
        point = vanishing_point_features.selected_vanishing_point
        _draw_cross(overlay, int(round(point.x)), int(round(point.y)), (0, 255, 255))

    lines = [
        f"yaw: {_display_angle(pose_result.yaw)}",
        f"pitch: {_display_angle(pose_result.pitch)}",
        f"roll: {_display_angle(pose_result.roll)}",
        f"confidence: {pose_result.confidence:.2f}",
    ]
    for index, text in enumerate(lines):
        cv2.putText(overlay, text, (24, 34 + index * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 4, cv2.LINE_AA)
        cv2.putText(overlay, text, (24, 34 + index * 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    paths = {"pose_overlay": debug_dir / "18_pose_overlay.png"}
    cv2.imwrite(str(paths["pose_overlay"]), overlay)
    return _string_paths(paths)


def _draw_lines(image: np.ndarray, lines: list[LineSegment], color: tuple[int, int, int]) -> np.ndarray:
    output = image.copy()
    for line in lines:
        cv2.line(output, (line.x1, line.y1), (line.x2, line.y2), color, 2)
    return output


def _draw_cross(image: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.line(image, (x - 12, y), (x + 12, y), color, 2)
    cv2.line(image, (x, y - 12), (x, y + 12), color, 2)


def _display_angle(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f} deg"


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
