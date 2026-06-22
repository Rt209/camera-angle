from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.contexts.motion_analysis.domain.flow_track import FlowVector
from src.contexts.pose_estimation.services.essential_pose_estimator import RelativePoseEstimate


def draw_uncalibrated_pose_overlay(
    frame_bgr: np.ndarray,
    vectors: list[FlowVector],
    pose: RelativePoseEstimate | None,
) -> np.ndarray:
    output = frame_bgr.copy()
    _draw_text_panel(output, pose)
    return output


def write_overlay_debug_frame(debug_dir: Path, frame_index: int, overlay_bgr: np.ndarray) -> str:
    debug_dir.mkdir(parents=True, exist_ok=True)
    path = debug_dir / f"pose_overlay_{frame_index:06d}.png"
    cv2.imwrite(str(path), overlay_bgr)
    return str(path)


def _draw_text_panel(image: np.ndarray, pose: RelativePoseEstimate | None) -> None:
    if pose is None:
        lines = [
            "UNCALIBRATED DEBUG PROTOTYPE",
            "intrinsics: approximate",
            "yaw_deg: N/A",
            "pitch_deg: N/A",
            "roll_deg: N/A",
            "warnings: no_pose_for_frame",
        ]
    else:
        lines = [
            "UNCALIBRATED DEBUG PROTOTYPE",
            "intrinsics: approximate",
            f"yaw_deg: {_fmt(pose.yaw_deg)}",
            f"pitch_deg: {_fmt(pose.pitch_deg)}",
            f"roll_deg: {_fmt(pose.roll_deg)}",
            f"tracked: {pose.tracked_point_count}  inliers: {pose.inlier_count}",
            f"inlier_ratio: {pose.inlier_ratio:.3f}  confidence: {pose.confidence:.3f}",
            "warnings: " + ", ".join(pose.warnings[:4]),
        ]
    x, y = 18, 24
    line_h = 22
    panel_w = min(image.shape[1] - 24, 650)
    panel_h = line_h * len(lines) + 16
    overlay = image.copy()
    cv2.rectangle(overlay, (10, 8), (10 + panel_w, 8 + panel_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.62, image, 0.38, 0.0, image)
    for index, text in enumerate(lines):
        color = (255, 255, 255) if index != 0 else (0, 220, 255)
        cv2.putText(image, text, (x, y + index * line_h), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"
