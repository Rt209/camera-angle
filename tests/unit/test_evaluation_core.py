from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from src.contexts.evaluation.services.frame_aligner import (
    align_geometry_prediction,
    align_optical_prediction,
)
from src.contexts.evaluation.services.metrics import (
    axis_statistics,
    error_jitter,
    geodesic_mae,
    p95_error,
    precision_at_theta,
    recall_at_theta,
)
from src.contexts.evaluation.services.oxts_loader import (
    load_reference_poses,
    parse_pose_text,
    require_reference,
)
from src.contexts.evaluation.services.prediction_reader import (
    read_geometry_predictions,
    read_optical_predictions,
)
from src.contexts.evaluation.services.rotation_error import (
    camera_motion_relative_rotation_zyx,
    conjugate_vehicle_delta_to_camera,
    geodesic_error_deg,
    relative_rotation_zyx,
    rotation_matrix_to_pose_angles,
    signed_angle_error,
    zyx_rotation_matrix,
)
from src.app.evaluation.geometry_service import GeometryEvaluationConfig
from src.app.evaluation.optical_flow_service import OpticalFlowEvaluationConfig


def test_oxts_loader_uses_numeric_filename_identity_and_sort(tmp_path: Path) -> None:
    for name, yaw in (("10.txt", 0.10), ("2.txt", 0.02), ("1.txt", 0.01)):
        (tmp_path / name).write_text(f"0 0 0 0 0 {yaw}", encoding="utf-8")

    references = load_reference_poses(tmp_path)

    assert list(references) == [1, 2, 10]
    assert references[10].source_frame_index == 10


def test_oxts_loader_reports_malformed_file_and_missing_required_frame(tmp_path: Path) -> None:
    malformed = tmp_path / "7.txt"
    malformed.write_text("0 0 0", encoding="utf-8")
    with pytest.raises(ValueError, match=r"7\.txt.*expected at least 6"):
        load_reference_poses(tmp_path)

    with pytest.raises(ValueError, match="required source frame index 4"):
        require_reference({}, 4)


def test_prediction_readers_accept_new_and_legacy_frame_identity(tmp_path: Path) -> None:
    geometry_csv = tmp_path / "geometry.csv"
    with geometry_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_index", "source_frame_index", "timestamp_sec", "yaw_deg", "pitch_deg", "roll_deg"])
        writer.writeheader()
        writer.writerow({"sample_index": 3, "source_frame_index": 8, "timestamp_sec": 0.8, "yaw_deg": 1, "pitch_deg": 2, "roll_deg": 3})
    record = read_geometry_predictions(geometry_csv)[0]
    assert (record.sample_index, record.source_frame_index) == (3, 8)

    legacy_csv = tmp_path / "legacy.csv"
    legacy_csv.write_text("frame_index,time_sec,yaw,pitch,roll\n9,0.9,1,2,3\n", encoding="utf-8")
    assert read_geometry_predictions(legacy_csv)[0].source_frame_index == 9

    optical_json = tmp_path / "optical.json"
    optical_json.write_text(json.dumps({"frames": [{"frame_index": 6, "yaw_deg": 1, "pitch_deg": 2, "roll_deg": 3}]}), encoding="utf-8")
    optical = read_optical_predictions(optical_json)[0]
    assert (optical.source_frame_index_prev, optical.source_frame_index_curr) == (5, 6)


def test_frame_alignment_never_uses_sample_index(tmp_path: Path) -> None:
    for index in (2, 4):
        (tmp_path / f"{index:010d}.txt").write_text("0 0 0 0 0 0", encoding="utf-8")
    references = load_reference_poses(tmp_path)

    geometry_csv = tmp_path / "geometry.csv"
    geometry_csv.write_text("sample_index,source_frame_index,yaw_deg,pitch_deg,roll_deg\n0,4,0,0,0\n", encoding="utf-8")
    geometry = align_geometry_prediction(read_geometry_predictions(geometry_csv)[0], references)
    assert geometry.reference.source_frame_index == 4

    optical_json = tmp_path / "optical.json"
    optical_json.write_text('{"frames":[{"sample_index":0,"source_frame_index_prev":2,"source_frame_index_curr":4,"yaw_deg":0,"pitch_deg":0,"roll_deg":0}]}', encoding="utf-8")
    optical = align_optical_prediction(read_optical_predictions(optical_json)[0], references)
    assert optical.previous_reference.source_frame_index == 2
    assert optical.reference.source_frame_index == 4


def test_rotation_and_metric_characterization_parity() -> None:
    assert np.allclose(zyx_rotation_matrix(0, 0, 0), np.eye(3))
    assert geodesic_error_deg((0, 0, 0), (0, 0, 0)) == 0.0
    assert signed_angle_error(-179, 179) == 2.0

    rows = [
        {"frame_index": 1, "pose_valid": True, "geodesic_error_deg": 0.5, "yaw_error": 1.0, "pitch_error": 0.0, "roll_error": 0.0},
        {"frame_index": 2, "pose_valid": False, "geodesic_error_deg": None, "yaw_error": None, "pitch_error": None, "roll_error": None},
    ]
    assert precision_at_theta(rows, 1.0) == 1.0
    assert recall_at_theta(rows, 1.0) == 0.5
    assert geodesic_mae(rows) == 0.5
    assert p95_error(rows) == 0.5
    assert error_jitter(rows) is None
    assert axis_statistics(rows, "yaw")["rmse"] == 1.0


def test_parse_labelled_pose_stays_degree_based() -> None:
    pose = parse_pose_text("yaw_deg: -70\npitch_deg: 2\nroll_deg: 1")
    assert pose is not None
    assert (pose.yaw_deg, pose.pitch_deg, pose.roll_deg) == (-70.0, 2.0, 1.0)


@pytest.mark.parametrize("config_type", [GeometryEvaluationConfig, OpticalFlowEvaluationConfig])
def test_evaluation_config_rejects_unsupported_rotation_contract(config_type: type) -> None:
    with pytest.raises(ValueError, match="rotation_order must be ZYX"):
        config_type(rotation_order="XYZ")
    with pytest.raises(ValueError, match="unit must be degree"):
        config_type(unit="radian")


def test_prediction_reader_rejects_conflicting_rotation_metadata(tmp_path: Path) -> None:
    path = tmp_path / "prediction.csv"
    path.write_text(
        "frame_index,yaw,pitch,roll,rotation_order,unit\n0,0,0,0,XYZ,degree\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="rotation_order must be ZYX"):
        read_geometry_predictions(path)


def test_relative_rotation_matrix_identity_axis_wrap_and_conjugation() -> None:
    identity = relative_rotation_zyx((10.0, -2.0, 3.0), (10.0, -2.0, 3.0))
    assert np.allclose(identity, np.eye(3), atol=1e-12)

    yaw_delta = relative_rotation_zyx((0.0, 0.0, 0.0), (15.0, 0.0, 0.0))
    assert np.allclose(rotation_matrix_to_pose_angles(yaw_delta), (15.0, 0.0, 0.0), atol=1e-12)

    wrapped = relative_rotation_zyx((179.0, 0.0, 0.0), (-179.0, 0.0, 0.0))
    assert np.allclose(rotation_matrix_to_pose_angles(wrapped), (2.0, 0.0, 0.0), atol=1e-12)

    camera_to_vehicle = zyx_rotation_matrix(90.0, 0.0, 0.0)
    vehicle_roll = zyx_rotation_matrix(0.0, 0.0, 10.0)
    camera_delta = conjugate_vehicle_delta_to_camera(vehicle_roll, camera_to_vehicle)
    expected = camera_to_vehicle.T @ vehicle_roll @ camera_to_vehicle
    assert np.allclose(camera_delta, expected, atol=1e-12)

    camera_motion = camera_motion_relative_rotation_zyx(
        (0.0, 0.0, 0.0), (15.0, 0.0, 0.0)
    )
    assert np.allclose(
        rotation_matrix_to_pose_angles(camera_motion),
        (-15.0, 0.0, 0.0),
        atol=1e-12,
    )


def test_optical_summary_becomes_comparison_ready_with_full_calibration() -> None:
    from src.contexts.evaluation.services.optical_flow_evaluator import build_summary

    rows = [
        {
            "frame_index": 1,
            "timestamp_sec": 0.1,
            "pose_valid": True,
            "status": "accepted",
            "geodesic_error_deg": 0.25,
            "raw_geodesic_error_deg": 0.25,
            "yaw_error": 0.1,
            "pitch_error": 0.1,
            "roll_error": 0.1,
            "pred_relative_yaw": 0.1,
            "pred_relative_pitch": 0.1,
            "pred_relative_roll": 0.1,
            "oxts_relative_yaw": 0.0,
            "oxts_relative_pitch": 0.0,
            "oxts_relative_roll": 0.0,
            "abs_yaw_error": 0.1,
            "abs_pitch_error": 0.1,
            "abs_roll_error": 0.1,
            "inlier_ratio": 0.8,
            "confidence": 0.7,
        }
    ]

    summary = build_summary(
        rows,
        extrinsics_applied=True,
        intrinsics_calibrated=True,
        extrinsics_source="kitti_raw:2011_09_26:image_03",
    )

    assert summary["comparison_ready"] is True
    assert summary["diagnostic_only"] is False
    assert summary["intrinsics_calibrated"] is True
    assert summary["extrinsics_applied"] is True
    assert summary["warnings"] == []
    assert summary["comparison_type"] == (
        "camera_relative_rotation_vs_camera_transformed_oxts_rotation"
    )
