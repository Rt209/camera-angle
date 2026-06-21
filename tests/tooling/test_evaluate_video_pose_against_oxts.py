from pathlib import Path
import csv
import json
import math

from tools.evaluation.evaluate_video_pose_against_oxts import (
    build_summary,
    build_worst_frames,
    evaluate_rows,
    read_pose_timeline,
    run_evaluation,
    write_evaluation_outputs,
)
from tools.dataset.kitti_pose_video import PoseAngles, load_poses


def _write_pose_csv(path: Path) -> None:
    rows = [
        {
            "frame_index": "0",
            "time_sec": "0.0",
            "yaw": "10",
            "pitch": "2",
            "roll": "1",
            "confidence": "0.9",
            "yaw_confidence": "0.8",
            "pitch_confidence": "0.7",
            "roll_confidence": "0.6",
            "status": "full",
            "detected_line_count": "20",
            "near_horizontal_count": "10",
            "near_vertical_count": "2",
            "perspective_line_count": "8",
            "vanishing_point_candidate_count": "4",
            "horizon_candidate_count": "3",
        },
        {
            "frame_index": "1",
            "time_sec": "0.1",
            "yaw": "",
            "pitch": "3",
            "roll": "-1",
            "confidence": "0.4",
            "yaw_confidence": "0",
            "pitch_confidence": "0.5",
            "roll_confidence": "0.5",
            "status": "partial",
            "detected_line_count": "5",
            "near_horizontal_count": "3",
            "near_vertical_count": "1",
            "perspective_line_count": "1",
            "vanishing_point_candidate_count": "0",
            "horizon_candidate_count": "1",
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_reads_pose_timeline_normal_and_missing_values(tmp_path: Path) -> None:
    pose_csv = tmp_path / "pose_timeline.csv"
    _write_pose_csv(pose_csv)

    rows = read_pose_timeline(pose_csv)

    assert rows[0]["yaw"] == 10.0
    assert rows[0]["detected_line_count"] == 20
    assert rows[1]["yaw"] is None
    assert rows[1]["status"] == "partial"


def test_loads_oxts_txt_and_converts_radians_to_degrees(tmp_path: Path) -> None:
    oxts_dir = tmp_path / "oxts"
    oxts_dir.mkdir()
    values = [0.0, 0.0, 0.0, math.radians(1.0), math.radians(2.0), math.radians(3.0)]
    (oxts_dir / "0000000000.txt").write_text(" ".join(str(value) for value in values), encoding="utf-8")

    poses = load_poses(oxts_dir)

    assert poses[0].roll_deg == 1.0
    assert poses[0].pitch_deg == 2.0
    assert poses[0].yaw_deg == 3.0000000000000004


def test_evaluates_error_and_handles_missing_angles(tmp_path: Path) -> None:
    pose_csv = tmp_path / "pose_timeline.csv"
    _write_pose_csv(pose_csv)
    rows = read_pose_timeline(pose_csv)

    evaluated = evaluate_rows(
        rows,
        [
            PoseAngles(yaw_deg=7.0, pitch_deg=1.0, roll_deg=0.5),
            PoseAngles(yaw_deg=20.0, pitch_deg=1.5, roll_deg=-2.0),
        ],
    )

    assert evaluated[0]["yaw_error"] == 3.0
    assert evaluated[0]["abs_yaw_error"] == 3.0
    assert evaluated[0]["pitch_error"] == 1.0
    assert evaluated[1]["yaw_error"] is None
    assert evaluated[1]["abs_yaw_error"] is None
    assert evaluated[1]["roll_error"] == 1.0


def test_summary_statistics_and_worst_frames_are_sorted(tmp_path: Path) -> None:
    evaluated = [
        {
            "frame_index": 0,
            "time_sec": 0.0,
            "pred_yaw": 10.0,
            "oxts_yaw": 7.0,
            "yaw_error": 3.0,
            "abs_yaw_error": 3.0,
            "pred_pitch": 2.0,
            "oxts_pitch": 1.0,
            "pitch_error": 1.0,
            "abs_pitch_error": 1.0,
            "pred_roll": 1.0,
            "oxts_roll": 0.5,
            "roll_error": 0.5,
            "abs_roll_error": 0.5,
            "confidence": 0.9,
            "status": "full",
            "detected_line_count": 20,
            "perspective_line_count": 8,
            "vanishing_point_candidate_count": 4,
            "horizon_candidate_count": 3,
        },
        {
            "frame_index": 1,
            "time_sec": 0.1,
            "pred_yaw": 2.0,
            "oxts_yaw": 10.0,
            "yaw_error": -8.0,
            "abs_yaw_error": 8.0,
            "pred_pitch": 3.0,
            "oxts_pitch": 1.5,
            "pitch_error": 1.5,
            "abs_pitch_error": 1.5,
            "pred_roll": -1.0,
            "oxts_roll": -2.0,
            "roll_error": 1.0,
            "abs_roll_error": 1.0,
            "confidence": 0.4,
            "status": "partial",
            "detected_line_count": 5,
            "perspective_line_count": 1,
            "vanishing_point_candidate_count": 0,
            "horizon_candidate_count": 1,
        },
    ]

    summary = build_summary(evaluated)
    worst = build_worst_frames(evaluated, limit=1)

    assert summary["valid_yaw_count"] == 2
    assert summary["mean_abs_yaw_error"] == 5.5
    assert round(summary["rmse_yaw_error"], 3) == 6.042
    assert summary["top_10_yaw_error_frames"][0]["frame_index"] == 1
    assert worst[0]["metric"] == "yaw"
    assert worst[0]["frame_index"] == 1


def test_writes_outputs_and_matplotlib_plots(tmp_path: Path) -> None:
    evaluated = evaluate_rows(
        [
            {
                "frame_index": 0,
                "time_sec": 0.0,
                "yaw": 10.0,
                "pitch": 2.0,
                "roll": 1.0,
                "confidence": 0.9,
                "yaw_confidence": 0.8,
                "pitch_confidence": 0.7,
                "roll_confidence": 0.6,
                "status": "full",
                "detected_line_count": 20,
                "near_horizontal_count": 10,
                "near_vertical_count": 2,
                "perspective_line_count": 8,
                "vanishing_point_candidate_count": 4,
                "horizon_candidate_count": 3,
            }
        ],
        [PoseAngles(yaw_deg=7.0, pitch_deg=1.0, roll_deg=0.5)],
    )

    outputs = write_evaluation_outputs(evaluated, tmp_path / "new" / "evaluation")

    assert outputs.comparison_csv.exists()
    assert outputs.summary_json.exists()
    assert outputs.worst_frames_csv.exists()
    assert (tmp_path / "new" / "evaluation").exists()
    for path in outputs.plot_paths.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_run_evaluation_writes_expected_files(tmp_path: Path) -> None:
    pose_csv = tmp_path / "pose_timeline.csv"
    _write_pose_csv(pose_csv)
    oxts_dir = tmp_path / "oxts"
    oxts_dir.mkdir()
    (oxts_dir / "0000000000.txt").write_text("0 0 0 0 0 0", encoding="utf-8")
    (oxts_dir / "0000000001.txt").write_text("0 0 0 0 0 0", encoding="utf-8")

    outputs = run_evaluation(pose_csv, oxts_dir, tmp_path / "evaluation")

    comparison_rows = list(csv.DictReader(outputs.comparison_csv.open(encoding="utf-8")))
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert len(comparison_rows) == 2
    assert summary["total_rows"] == 2
