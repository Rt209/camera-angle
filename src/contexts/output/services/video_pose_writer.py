from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from src.shared.errors import VideoOutputError


CSV_COLUMNS = [
    "frame_index",
    "time_sec",
    "yaw",
    "pitch",
    "roll",
    "raw_yaw",
    "raw_pitch",
    "raw_roll",
    "smoothed_yaw",
    "smoothed_pitch",
    "smoothed_roll",
    "confidence",
    "yaw_confidence",
    "pitch_confidence",
    "roll_confidence",
    "status",
    "warnings",
    "detected_line_count",
    "near_horizontal_count",
    "near_vertical_count",
    "perspective_line_count",
    "vanishing_point_candidate_count",
    "horizon_candidate_count",
    "selected_horizon_y_at_center",
    "selected_vanishing_point_x",
    "selected_vanishing_point_y",
]


class SerializableFrameResult(Protocol):
    frame_index: int
    time_sec: float
    status: str
    frame_bgr: np.ndarray | None

    def to_timeline_row(self) -> dict[str, Any]:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


def write_pose_timeline_csv(results: list[SerializableFrameResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            row = result.to_timeline_row()
            row["warnings"] = json.dumps(row.get("warnings") or [], ensure_ascii=True)
            writer.writerow({column: row.get(column) for column in CSV_COLUMNS})


def write_frame_results_json(
    results: list[SerializableFrameResult],
    output_path: Path,
    video_metadata: dict[str, Any],
    sampling_config: dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_metadata": video_metadata,
        "sampling_config": sampling_config,
        "frames": [result.to_dict() for result in results],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def write_predicted_overlay_video(
    results: list[SerializableFrameResult],
    output_path: Path,
    fps: float,
    size: tuple[int, int],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise VideoOutputError(f"Could not open video writer for: {output_path}")

    try:
        for result in results:
            if result.frame_bgr is None:
                continue
            frame = result.frame_bgr.copy()
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            writer.write(draw_pose_text_overlay(frame, result.to_timeline_row()))
    finally:
        writer.release()


def draw_pose_text_overlay(frame: np.ndarray, row: dict[str, Any]) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = max(0.45, min(width, height) / 950.0)
    thickness = max(1, round(scale * 2))
    line_height = int(24 * scale)
    padding = int(12 * scale)
    origin_x = padding
    origin_y = padding + line_height
    lines = [
        f"Frame {row['frame_index']}  t={row['time_sec']:.2f}s",
        f"Yaw   {_angle(row.get('yaw'))}",
        f"Pitch {_angle(row.get('pitch'))}",
        f"Roll  {_angle(row.get('roll'))}",
        f"Conf  {_number(row.get('confidence'))}  {row.get('status', 'unknown')}",
    ]
    box_width = int(max(cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0] for line in lines) + padding * 2)
    box_height = line_height * len(lines) + padding

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (box_width, box_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, frame)

    for index, text in enumerate(lines):
        y = origin_y + index * line_height
        cv2.putText(frame, text, (origin_x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return frame


def _angle(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):7.2f} deg"


def _number(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2f}"
