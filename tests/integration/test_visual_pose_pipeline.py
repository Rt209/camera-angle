from pathlib import Path
import json

import cv2
import numpy as np

from src.app.pipeline import run_visual_pose_pipeline
from src.contexts.geometry_features.services.line_detector import LineDetectionConfig
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig


def test_visual_pose_pipeline_outputs_roll_and_debug_artifacts(tmp_path: Path) -> None:
    image_path = tmp_path / "rotated_lines.png"
    debug_dir = tmp_path / "debug"
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    cv2.line(image, (30, 90), (290, 110), (0, 0, 0), 4)
    cv2.line(image, (40, 150), (280, 168), (0, 0, 0), 4)
    cv2.imwrite(str(image_path), image)

    result = run_visual_pose_pipeline(
        image_path,
        debug_dir,
        preprocess_config=PreprocessConfig(max_width=640),
        line_config=LineDetectionConfig(threshold=25, min_line_length=40, max_line_gap=8),
    )
    data = result.to_dict()

    assert data["yaw"] is None
    assert data["pitch"] is None
    assert data["roll"] is not None
    assert data["unit"] == "degree"
    assert data["method"] == "geometry_based_partial_pose_estimation"
    assert data["stage"] == "stage_0_3_foundation_and_roll"
    assert data["features_used"] == ["edges", "lines"]
    assert data["warnings"] == []
    assert set(data) == {
        "image",
        "yaw",
        "pitch",
        "roll",
        "unit",
        "confidence",
        "method",
        "stage",
        "features_used",
        "debug_artifacts",
        "warnings",
        "line_features",
    }
    assert set(data["line_features"]) == {
        "detected_line_count",
        "filtered_line_count",
        "near_horizontal_count",
        "near_vertical_count",
        "lines",
    }
    assert set(data["debug_artifacts"]) == {
        "input",
        "grayscale",
        "blurred",
        "edges",
        "detected_lines",
        "lines",
        "line_orientation_debug",
        "roll_candidate_lines",
        "roll_orientation_histogram",
        "roll_overlay",
    }
    for path in data["debug_artifacts"].values():
        assert Path(path).exists()
    json.dumps(data)


def test_visual_pose_pipeline_handles_images_without_roll_candidates(tmp_path: Path) -> None:
    image_path = tmp_path / "blank.png"
    debug_dir = tmp_path / "debug"
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(image_path), image)

    result = run_visual_pose_pipeline(
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
    assert data["warnings"] == [
        "Roll could not be estimated because no stable horizontal or vertical line candidates were found."
    ]
    assert data["line_features"]["detected_line_count"] == 0
    assert data["line_features"]["filtered_line_count"] == 0
    assert Path(data["debug_artifacts"]["roll_overlay"]).exists()
    assert Path(data["debug_artifacts"]["roll_orientation_histogram"]).exists()
