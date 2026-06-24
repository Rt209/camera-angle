import csv
import json
from pathlib import Path
from datetime import datetime

import pytest

from src.app.evaluation.geometry_service import (
    GeometryEvaluationConfig,
    evaluate_geometry_pose,
    evaluate_standalone_geometry_pose,
)
from src.app.evaluation.optical_flow_service import (
    OpticalFlowEvaluationConfig,
    evaluate_optical_flow_pose,
    evaluate_standalone_optical_flow_pose,
)
from src.app.evaluation.output_directory import resolve_evaluation_output_directory
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService


def _references(path: Path) -> None:
    path.mkdir()
    for index in range(2):
        (path / f"{index:010d}.txt").write_text("0 0 0 0 0 0", encoding="utf-8")


def test_geometry_application_service_writes_canonical_compact_artifacts(tmp_path: Path) -> None:
    prediction = tmp_path / "pose_timeline.csv"
    with prediction.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_index", "source_frame_index", "yaw_deg", "pitch_deg", "roll_deg", "comparison_ready"])
        writer.writeheader()
        writer.writerow({"sample_index": 0, "source_frame_index": 0, "yaw_deg": 0, "pitch_deg": 0, "roll_deg": 0, "comparison_ready": "false"})
    references = tmp_path / "oxts"
    _references(references)

    output_dir = tmp_path / "eval/geometry"
    outputs = evaluate_geometry_pose(prediction, references, output_dir, GeometryEvaluationConfig())
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))

    assert {path.name for path in output_dir.iterdir()} == {"per_frame.csv", "summary.json", "evaluation_report.md"}
    assert summary["diagnostic_only"] is True
    assert "raw_geometry_yaw" in summary["warnings"][0]
    report = outputs.report_md.read_text(encoding="utf-8")
    assert summary["rotation_order"] == "ZYX" and "Rotation order: ZYX" in report
    assert summary["unit"] == "degree" and "Unit: degree" in report


def test_optical_application_service_preserves_relative_semantics_and_options(tmp_path: Path) -> None:
    prediction = tmp_path / "frame_pose_results.json"
    prediction.write_text(json.dumps({"frames": [{"sample_index": 0, "source_frame_index_prev": 0, "source_frame_index_curr": 1, "yaw_deg": 0, "pitch_deg": 0, "roll_deg": 0, "warnings": ["intrinsics_not_calibrated"]}]}), encoding="utf-8")
    references = tmp_path / "oxts"
    _references(references)

    output_dir = tmp_path / "eval/optical"
    outputs = evaluate_optical_flow_pose(
        prediction,
        references,
        output_dir,
        OpticalFlowEvaluationConfig(save_worst_frames=True),
    )
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))

    assert outputs.worst_frames_csv is not None and outputs.worst_frames_csv.exists()
    assert not (output_dir / "plots").exists()
    assert summary["pose_type"] == "frame_to_frame_relative_rotation"
    assert "intrinsics_not_calibrated" in summary["warnings"]
    report = outputs.report_md.read_text(encoding="utf-8")
    assert summary["rotation_order"] == "ZYX" and "Rotation order: ZYX" in report
    assert summary["unit"] == "degree" and "Unit: degree" in report


def test_missing_input_does_not_leave_default_run_directory(tmp_path: Path) -> None:
    paths = RepositoryPaths(tmp_path)
    service = RunDirectoryService(
        paths.outputs_root, lambda: datetime(2026, 6, 22, 14, 15, 16)
    )
    output_dir = resolve_evaluation_output_directory(
        "geometry", None, repository_paths=paths, run_directory_service=service
    )

    with pytest.raises((OSError, ValueError)):
        evaluate_geometry_pose(
            tmp_path / "missing-prediction.csv",
            tmp_path / "missing-oxts",
            output_dir,
        )

    assert not paths.outputs_root.exists()
    assert not output_dir.exists()


def test_standalone_evaluations_reserve_run_and_write_manifest(tmp_path: Path) -> None:
    paths = RepositoryPaths(tmp_path)
    references = tmp_path / "oxts"
    _references(references)

    geometry_prediction = tmp_path / "geometry.csv"
    geometry_prediction.write_text(
        "source_frame_index,yaw_deg,pitch_deg,roll_deg\n0,0,0,0\n",
        encoding="utf-8",
    )
    geometry_service = RunDirectoryService(
        paths.outputs_root,
        lambda: datetime(2026, 6, 22, 15, 30, 45, 123000),
    )
    geometry = evaluate_standalone_geometry_pose(
        geometry_prediction,
        references,
        paths,
        run_directory_service=geometry_service,
    )
    geometry_run = paths.outputs_root / "20260622_153045_123"
    assert geometry.comparison_csv == geometry_run / "eval/geometry/per_frame.csv"
    geometry_manifest = json.loads(
        (geometry_run / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert geometry_manifest["selected_tasks"] == ["eval_geometry"]
    assert not (geometry_run / "geometry").exists()
    assert not (geometry_run / "optical").exists()

    optical_prediction = tmp_path / "optical.json"
    optical_prediction.write_text(
        '{"frames":[{"source_frame_index_prev":0,"source_frame_index_curr":1,"yaw_deg":0,"pitch_deg":0,"roll_deg":0}]}',
        encoding="utf-8",
    )
    optical_service = RunDirectoryService(
        paths.outputs_root,
        lambda: datetime(2026, 6, 22, 15, 30, 45, 123000),
    )
    optical = evaluate_standalone_optical_flow_pose(
        optical_prediction,
        references,
        paths,
        run_directory_service=optical_service,
    )
    optical_run = paths.outputs_root / "20260622_153045_123_01"
    assert optical.comparison_csv == optical_run / "eval/optical/per_frame.csv"
    optical_manifest = json.loads(
        (optical_run / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert optical_manifest["selected_tasks"] == ["eval_optical"]
    assert not (optical_run / "eval/geometry").exists()
