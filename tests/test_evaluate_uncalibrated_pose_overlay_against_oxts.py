from __future__ import annotations

from tools.evaluate_uncalibrated_pose_overlay_against_oxts import build_summary, evaluate_rows
from tools.kitti_pose_video import PoseAngles


def test_uncalibrated_pose_evaluation_compares_oxts_frame_delta() -> None:
    pose_rows = [
        {
            "frame_index": 1,
            "timestamp_sec": 0.1,
            "yaw_deg": 2.5,
            "pitch_deg": -0.5,
            "roll_deg": 0.25,
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
    assert rows[0]["oxts_relative_yaw"] == 2.0
    assert rows[0]["yaw_error"] == 0.5
    assert rows[0]["oxts_relative_pitch"] == -0.5
    assert rows[0]["pitch_error"] == 0.0
    assert summary["comparison_type"] == "predicted_frame_to_frame_relative_rotation_vs_oxts_frame_to_frame_delta"
    assert summary["calibrated_pose_result"] is False

