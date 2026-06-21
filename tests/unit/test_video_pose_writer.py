from pathlib import Path
import csv
import json

import cv2
import numpy as np
import pytest

from src.app.video_pipeline import VideoPoseFrameResult
from src.contexts.pose_estimation.services.yaw_reliability_gate import apply_video_yaw_reliability
from src.contexts.output.services.video_pose_writer import (
    write_frame_results_json,
    write_pose_timeline_csv,
    write_predicted_overlay_video,
)


def _partial_result() -> VideoPoseFrameResult:
    return VideoPoseFrameResult(
        frame_index=10,
        time_sec=1.0,
        status="partial",
        frame_bgr=np.full((48, 64, 3), 120, dtype=np.uint8),
        pose_result={
            "yaw": None,
            "pitch": 1.25,
            "roll": -0.5,
            "confidence": 0.4,
            "angle_confidence": {"yaw": 0.0, "pitch": 0.6, "roll": 0.6},
        },
        feature_metadata={
            "line_features": {
                "detected_line_count": 3,
                "near_horizontal_count": 1,
                "near_vertical_count": 1,
            },
            "horizon_features": {
                "candidate_count": 1,
                "selected_horizon": {"y_at_center": 24.0},
            },
            "vanishing_point_features": {
                "perspective_line_count": 1,
                "candidate_count": 0,
                "selected_vanishing_point": None,
            },
        },
        warnings=["Yaw could not be estimated."],
    )


def test_timeline_writer_serializes_partial_result_and_warnings(tmp_path: Path) -> None:
    output_path = tmp_path / "pose_timeline.csv"

    write_pose_timeline_csv([_partial_result()], output_path)

    text = output_path.read_text(encoding="utf-8")
    assert "frame_index,time_sec" in text
    assert "partial" in text
    assert "Yaw could not be estimated." in text
    assert ",1.25,-0.5," in text


def test_yaw_reliability_columns_are_written_without_runtime_calibration(tmp_path: Path) -> None:
    first = VideoPoseFrameResult(
        frame_index=0,
        time_sec=0.0,
        status="full",
        frame_bgr=np.full((48, 64, 3), 120, dtype=np.uint8),
        pose_result={
            "yaw": -20.0,
            "pitch": 1.0,
            "roll": 0.5,
            "confidence": 0.9,
            "angle_confidence": {"yaw": 0.9, "pitch": 0.9, "roll": 0.9},
        },
        feature_metadata={
            "line_features": {"detected_line_count": 8, "near_horizontal_count": 2, "near_vertical_count": 1},
            "horizon_features": {"candidate_count": 1, "selected_horizon": {"y_at_center": 24.0}},
            "vanishing_point_features": {
                "perspective_line_count": 8,
                "candidate_count": 12,
                "selected_vanishing_point": {"x": 20.0, "y": 18.0},
                "cluster_ambiguity": 0.1,
                "line_support_consistency": 0.9,
                "selected_cluster_id": 1,
                "second_best_cluster_id": 2,
            },
        },
        warnings=[],
    )
    second = VideoPoseFrameResult(
        frame_index=1,
        time_sec=0.1,
        status="full",
        frame_bgr=np.full((48, 64, 3), 120, dtype=np.uint8),
        pose_result={
            "yaw": 15.0,
            "pitch": 1.0,
            "roll": 0.5,
            "confidence": 0.9,
            "angle_confidence": {"yaw": 0.9, "pitch": 0.9, "roll": 0.9},
        },
        feature_metadata={
            "line_features": {"detected_line_count": 8, "near_horizontal_count": 2, "near_vertical_count": 1},
            "horizon_features": {"candidate_count": 1, "selected_horizon": {"y_at_center": 24.0}},
            "vanishing_point_features": {
                "perspective_line_count": 8,
                "candidate_count": 12,
                "selected_vanishing_point": {"x": 60.0, "y": 18.0},
                "cluster_ambiguity": 0.8,
                "line_support_consistency": 0.2,
                "selected_cluster_id": 2,
                "second_best_cluster_id": 1,
            },
        },
        warnings=[],
    )
    apply_video_yaw_reliability([first, second], image_width=64)

    output_path = tmp_path / "pose_timeline.csv"
    write_pose_timeline_csv([first, second], output_path)

    with output_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert rows[1]["raw_vp_yaw"] == "15.0"
    assert rows[1]["image_geometry_yaw"] == "15.0"
    assert rows[1]["yaw"] == "-15.0"
    assert rows[1]["calibrated_heading_yaw"] == ""
    assert rows[1]["comparison_ready"] == "False"
    assert rows[1]["pose_semantics"] == "single_frame_vanishing_point_image_geometry_yaw"
    assert rows[1]["vp_side_flip"] == "True"
    assert rows[1]["selected_cluster_id"] == "2"
    assert "yaw_sign_reference_flip" in json.loads(rows[1]["yaw_warning_flags"])
    assert "high_cluster_ambiguity" in json.loads(rows[1]["yaw_warning_flags"])


def test_json_writer_handles_missing_feature_metadata(tmp_path: Path) -> None:
    output_path = tmp_path / "frame_pose_results.json"
    result = VideoPoseFrameResult.failed(0, 0.0, None, "pipeline failed")

    write_frame_results_json([result], output_path, {"fps": 10.0}, {"sample_every": 1})

    text = output_path.read_text(encoding="utf-8")
    assert '"video_metadata"' in text
    assert '"failure_reason": "pipeline failed"' in text


def test_writers_handle_empty_results(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    json_path = tmp_path / "empty.json"

    write_pose_timeline_csv([], csv_path)
    write_frame_results_json([], json_path, {"fps": 10.0}, {"sample_every": 1})

    assert csv_path.read_text(encoding="utf-8").startswith("frame_index,time_sec")
    assert '"frames": []' in json_path.read_text(encoding="utf-8")


def test_overlay_writer_on_and_invalid_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "predicted_pose_overlay.mp4"

    write_predicted_overlay_video([_partial_result()], output_path, fps=5.0, size=(64, 48))

    capture = cv2.VideoCapture(str(output_path))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 1
    finally:
        capture.release()

    with pytest.raises(Exception):
        write_predicted_overlay_video([_partial_result()], tmp_path, fps=5.0, size=(64, 48))
