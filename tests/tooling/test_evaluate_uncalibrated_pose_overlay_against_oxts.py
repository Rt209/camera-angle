from __future__ import annotations

from src.contexts.evaluation.services.optical_flow_evaluator import (
    build_summary,
    evaluate_rows,
    run_evaluation,
)
from src.contexts.evaluation.domain.pose_record import PoseAngles
from src.contexts.evaluation.services.rotation_error import (
    camera_motion_relative_rotation_zyx,
    rotation_matrix_to_pose_angles,
)


def test_uncalibrated_pose_evaluation_compares_oxts_frame_delta() -> None:
    pose_rows = [
        {
            "frame_index": 1,
            "timestamp_sec": 0.1,
            "yaw_deg": -1.9930553597507359,
            "pitch_deg": 0.5264326237270068,
            "roll_deg": -0.2329749682655731,
            "tracked_point_count": 120,
            "inlier_count": 80,
            "inlier_ratio": 0.66,
            "confidence": 0.2,
            "warnings": ["intrinsics_not_calibrated"],
        }
    ]
    oxts = [
        PoseAngles(yaw_deg=10.0, pitch_deg=1.0, roll_deg=-1.0),
        PoseAngles(yaw_deg=12.0, pitch_deg=0.5, roll_deg=-0.75),
    ]

    rows = evaluate_rows(pose_rows, oxts)
    summary = build_summary(rows)

    assert rows[0]["oxts_absolute_yaw"] == 12.0
    expected = rotation_matrix_to_pose_angles(
        camera_motion_relative_rotation_zyx((10.0, 1.0, -1.0), (12.0, 0.5, -0.75))
    )
    assert rows[0]["oxts_relative_yaw"] == expected[0]
    assert rows[0]["oxts_relative_pitch"] == expected[1]
    assert rows[0]["oxts_relative_roll"] == expected[2]
    assert rows[0]["legacy_oxts_relative_yaw"] == 2.0
    assert rows[0]["legacy_oxts_relative_pitch"] == -0.5
    assert (
        summary["comparison_type"]
        == "camera_relative_rotation_vs_vehicle_relative_rotation_without_extrinsics"
    )
    assert summary["relative_rotation_method"] == (
        "R_current_transpose_times_R_previous_ZYX_camera_motion"
    )
    assert summary["extrinsics_applied"] is False
    assert summary["diagnostic_only"] is True
    assert summary["calibrated_pose_result"] is False
    metrics = summary["selected_metrics"]
    assert metrics["theta_deg"] == 1.0
    assert metrics["precision_at_theta"] == 1.0
    assert metrics["recall_at_theta"] == 1.0
    assert metrics["geodesic_mae_deg"] == rows[0]["geodesic_error_deg"]
    assert metrics["p95_error_deg"] == rows[0]["geodesic_error_deg"]
    assert metrics["jitter_deg"] is None


def test_selected_metrics_include_invalid_pose_in_recall_denominator() -> None:
    pose_rows = [
        {"frame_index": 1, "yaw_deg": 0.5, "pitch_deg": 0.0, "roll_deg": 0.0},
        {"frame_index": 2, "yaw_deg": None, "pitch_deg": None, "roll_deg": None},
    ]
    oxts = [
        PoseAngles(yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0),
        PoseAngles(yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0),
        PoseAngles(yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0),
    ]

    rows = evaluate_rows(pose_rows, oxts)
    summary = build_summary(rows, theta_deg=1.0)

    assert summary["selected_metrics"]["precision_at_theta"] == 1.0
    assert summary["selected_metrics"]["recall_at_theta"] == 0.5
    assert summary["selected_metrics"]["valid_prediction_count"] == 1


def test_rejected_pose_keeps_raw_metrics_and_recall_denominator() -> None:
    pose_rows = [{
        "frame_index": 1, "yaw_deg": None, "pitch_deg": None, "roll_deg": None,
        "raw_yaw_deg": 40.0, "raw_pitch_deg": 0.0, "raw_roll_deg": 0.0,
        "status": "rejected", "rejection_reason": "temporal_rotation_jump",
    }]
    oxts = [PoseAngles(0.0, 0.0, 0.0), PoseAngles(0.0, 0.0, 0.0)]

    summary = build_summary(evaluate_rows(pose_rows, oxts), theta_deg=1.0)

    assert summary["pose_status_counts"]["rejected"] == 1
    assert summary["raw_metrics"]["catastrophic_error_count"] == 1
    assert summary["accepted_metrics"]["valid_prediction_count"] == 0
    assert summary["accepted_metrics"]["recall_denominator"] == 1


def test_run_evaluation_writes_compact_outputs_by_default(tmp_path) -> None:
    pose_json = tmp_path / "pose.json"
    pose_json.write_text(
        '{"frames": [{"frame_index": 1, "yaw_deg": 0.0, "pitch_deg": 0.0, "roll_deg": 0.0}]}',
        encoding="utf-8",
    )
    oxts_dir = tmp_path / "oxts"
    oxts_dir.mkdir()
    (oxts_dir / "0000000000.txt").write_text("0 0 0 0 0 0", encoding="utf-8")
    (oxts_dir / "0000000001.txt").write_text("0 0 0 0 0 0", encoding="utf-8")

    outputs = run_evaluation(pose_json, oxts_dir, tmp_path / "evaluation")

    assert outputs.comparison_csv.name == "per_frame.csv"
    assert outputs.summary_json.name == "summary.json"
    assert outputs.report_md.exists()
    assert outputs.worst_frames_csv is None
    assert outputs.plot_paths == {}
    assert sorted(path.name for path in (tmp_path / "evaluation").iterdir()) == [
        "evaluation_report.md",
        "per_frame.csv",
        "summary.json",
    ]
