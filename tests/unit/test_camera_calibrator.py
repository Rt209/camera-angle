from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.contexts.camera_model.services.calibration_board_detector import CalibrationBoardConfig, CalibrationBoardDetector
from src.contexts.camera_model.services.calibration_frame_sampler import CalibrationFrameSamplerConfig
from src.contexts.camera_model.services.camera_calibrator import CameraCalibrationConfig, CameraCalibrator


def _synthetic_calibration_points(
    board_rows: int = 6,
    board_cols: int = 9,
    square_size: float = 0.04,
    image_size: tuple[int, int] = (640, 480),
    views: int = 10,
) -> tuple[list[np.ndarray], list[np.ndarray], tuple[int, int]]:
    detector = CalibrationBoardDetector(
        CalibrationBoardConfig(board_rows=board_rows, board_cols=board_cols, square_size=square_size)
    )
    object_template = detector.object_points_template()
    camera_matrix = np.array([[820.0, 0.0, 321.0], [0.0, 815.0, 239.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    dist_coeffs = np.zeros((5, 1), dtype=np.float64)
    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []

    for index in range(views):
        rvec = np.array(
            [
                -0.20 + index * 0.035,
                0.16 * np.sin(index * 0.7),
                -0.10 + index * 0.018,
            ],
            dtype=np.float64,
        )
        tvec = np.array(
            [
                -0.08 + index * 0.018,
                -0.04 + index * 0.010,
                0.65 + index * 0.025,
            ],
            dtype=np.float64,
        )
        projected, _ = cv2.projectPoints(object_template, rvec, tvec, camera_matrix, dist_coeffs)
        object_points.append(object_template.astype(np.float32))
        image_points.append(projected.reshape(-1, 2).astype(np.float32))

    return object_points, image_points, image_size


def _draw_chessboard_view(
    board_rows: int,
    board_cols: int,
    square_px: int,
    image_size: tuple[int, int],
    index: int,
) -> np.ndarray:
    square_count_x = board_cols + 1
    square_count_y = board_rows + 1
    board_w = square_count_x * square_px
    board_h = square_count_y * square_px
    texture = np.full((board_h, board_w), 255, dtype=np.uint8)
    for y in range(square_count_y):
        for x in range(square_count_x):
            if (x + y) % 2 == 0:
                cv2.rectangle(
                    texture,
                    (x * square_px, y * square_px),
                    ((x + 1) * square_px, (y + 1) * square_px),
                    0,
                    -1,
                )

    width, height = image_size
    margin_x = 70 + index * 8
    margin_y = 45 + index * 5
    wobble = index * 4
    dst = np.array(
        [
            [margin_x + wobble, margin_y],
            [width - 90 + wobble // 2, margin_y + 12 + index],
            [width - 72 - wobble, height - 58],
            [margin_x - 25, height - 48 - index],
        ],
        dtype=np.float32,
    )
    src = np.array([[0, 0], [board_w - 1, 0], [board_w - 1, board_h - 1], [0, board_h - 1]], dtype=np.float32)
    homography = cv2.getPerspectiveTransform(src, dst)
    canvas = np.full((height, width), 180, dtype=np.uint8)
    mask = cv2.warpPerspective(np.full_like(texture, 255), homography, image_size)
    warped = cv2.warpPerspective(texture, homography, image_size)
    canvas[mask > 0] = warped[mask > 0]
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def _write_synthetic_chessboard_video(path: Path, board_rows: int = 6, board_cols: int = 9) -> None:
    image_size = (640, 480)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8.0, image_size)
    assert writer.isOpened()
    try:
        for index in range(10):
            writer.write(_draw_chessboard_view(board_rows, board_cols, 42, image_size, index))
    finally:
        writer.release()


def test_camera_calibrator_calibrates_from_projected_points() -> None:
    object_points, image_points, image_size = _synthetic_calibration_points()
    config = CameraCalibrationConfig(min_valid_frames=5, source_label="synthetic_fixture_points")
    result = CameraCalibrator(config).calibrate_from_points(object_points, image_points, image_size)

    assert result.intrinsics.camera_matrix.shape == (3, 3)
    assert result.intrinsics.dist_coeffs.size >= 5
    assert result.intrinsics.image_width == 640
    assert result.intrinsics.image_height == 480
    assert result.reprojection_error < 0.05
    assert result.source == "synthetic_fixture_points"


def test_camera_calibrator_writes_required_debug_outputs(tmp_path: Path) -> None:
    video_path = tmp_path / "synthetic_calibration.avi"
    _write_synthetic_chessboard_video(video_path)
    debug_root = tmp_path / "calibration_debug"
    output_json = debug_root / "camera_intrinsics.json"
    report_path = debug_root / "calibration_report.md"
    detected_dir = debug_root / "detected_corners"

    config = CameraCalibrationConfig(
        board=CalibrationBoardConfig(pattern="chessboard", board_rows=6, board_cols=9, square_size=1.0),
        sampler=CalibrationFrameSamplerConfig(frame_step=1, max_frames=10),
        min_valid_frames=4,
        source_label="synthetic_fixture_calibration_video",
    )
    calibrator = CameraCalibrator(config)
    result = calibrator.calibrate_from_video(video_path, detected_dir)
    calibrator.write_outputs(result, output_json, report_path)

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["camera_matrix"][2] == [0.0, 0.0, 1.0]
    assert len(payload["dist_coeffs"]) >= 5
    assert payload["image_width"] == 640
    assert payload["image_height"] == 480
    assert payload["reprojection_error"] >= 0.0
    assert payload["source"] == "synthetic_fixture_calibration_video"
    assert result.calibration_frame_count >= 4
    assert len(list(detected_dir.glob("*_corners.png"))) >= 4
    assert "synthetic / fixture" in report_path.read_text(encoding="utf-8")


def test_camera_calibrator_rejects_too_few_valid_frames() -> None:
    object_points, image_points, image_size = _synthetic_calibration_points(views=2)
    config = CameraCalibrationConfig(min_valid_frames=5)

    with pytest.raises(RuntimeError, match="Need at least 5 valid calibration frames"):
        CameraCalibrator(config).calibrate_from_points(object_points, image_points, image_size)


def test_charuco_pattern_reports_clear_environment_error() -> None:
    detector = CalibrationBoardDetector(CalibrationBoardConfig(pattern="charuco", board_rows=6, board_cols=9))
    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    with pytest.raises(RuntimeError, match="Charuco calibration requires|not wired yet"):
        detector.detect(frame)
