from pathlib import Path
import json

import cv2
import numpy as np

from src.app.pipeline import run_stage_4_7_pose_pipeline
from src.contexts.geometry_features.services.line_detector import LineDetectionConfig
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig


def test_stage_4_7_pipeline_outputs_pose_integration_and_debug_artifacts(tmp_path: Path) -> None:
    image_path = tmp_path / "corridor_like.png"
    debug_dir = tmp_path / "debug"
    image = np.full((260, 360, 3), 255, dtype=np.uint8)
    cv2.line(image, (30, 95), (330, 95), (0, 0, 0), 4)
    cv2.line(image, (20, 230), (180, 105), (0, 0, 0), 4)
    cv2.line(image, (340, 230), (180, 105), (0, 0, 0), 4)
    cv2.imwrite(str(image_path), image)

    result = run_stage_4_7_pose_pipeline(
        image_path,
        debug_dir,
        preprocess_config=PreprocessConfig(max_width=720),
        line_config=LineDetectionConfig(threshold=25, min_line_length=40, max_line_gap=8),
    )
    data = result.to_dict()

    assert data["stage"] == "stage_4_7_pose_integration_and_debug"
    assert data["pitch"] is not None
    assert data["yaw"] is not None
    assert data["angle_confidence"]["pitch"] > 0
    assert data["angle_confidence"]["yaw"] > 0
    assert "horizon" in data["features_used"]
    assert "vanishing_point" in data["features_used"]
    assert data["horizon_features"]["selected_horizon"] is not None
    assert data["vanishing_point_features"]["selected_vanishing_point"] is not None
    assert Path(data["debug_artifacts"]["horizon"]).exists()
    assert Path(data["debug_artifacts"]["vanishing_point"]).exists()
    assert Path(data["debug_artifacts"]["pose_overlay"]).exists()
    json.dumps(data)


def test_stage_4_7_pipeline_handles_blank_image_as_partial_result(tmp_path: Path) -> None:
    image_path = tmp_path / "blank.png"
    debug_dir = tmp_path / "debug"
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(image_path), image)

    result = run_stage_4_7_pose_pipeline(
        image_path,
        debug_dir,
        preprocess_config=PreprocessConfig(max_width=640),
        line_config=LineDetectionConfig(threshold=25, min_line_length=40, max_line_gap=8),
    )
    data = result.to_dict()

    assert data["yaw"] is None
    assert data["pitch"] is None
    assert data["roll"] is None
    assert data["confidence"] == 0.0
    assert data["angle_confidence"] == {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
    assert data["warnings"]
    assert Path(data["debug_artifacts"]["pose_overlay"]).exists()


def test_stage_4_7_pipeline_estimates_yaw_for_example_zero(tmp_path: Path) -> None:
    image_path = Path("examples/0.png")
    if not image_path.exists():
        return

    result = run_stage_4_7_pose_pipeline(
        image_path,
        tmp_path / "debug",
    )
    data = result.to_dict()

    assert data["yaw"] is not None
    assert data["angle_confidence"]["yaw"] > 0
    assert data["vanishing_point_features"]["selected_vanishing_point"] is not None
    assert "vanishing_point" in data["features_used"]


def test_stage_4_7_pipeline_improves_example_zero_pose_errors(tmp_path: Path) -> None:
    image_path = Path("examples/0.png")
    if not image_path.exists():
        return

    result = run_stage_4_7_pose_pipeline(
        image_path,
        tmp_path / "debug",
    )
    data = result.to_dict()

    assert data["yaw"] is not None
    assert data["pitch"] is not None
    assert data["roll"] is not None

    assert abs(data["yaw"] - (-70.010)) < 10.0
    assert abs(data["pitch"] - 0.000573) < 4.159427
    assert abs(data["roll"] - 1.286) < 3.176
