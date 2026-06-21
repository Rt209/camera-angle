from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.contexts.motion_analysis.domain.flow_track import FlowVector
from tools.optical_flow.debug_optical_flow_pose_parameters import (
    PROJECT_ROOT,
    _frame_payload,
    _prepare_dir,
    _render_deep_dive_report,
)


def test_frame_payload_preserves_pose_oxts_and_warning_fields() -> None:
    pose = SimpleNamespace(
        tracked_point_count=120,
        inlier_count=70,
        inlier_ratio=0.58,
        yaw_deg=1.2,
        pitch_deg=-0.4,
        roll_deg=0.1,
        confidence=0.18,
        warnings=["intrinsics_not_calibrated", "approximate_K_used", "pose_for_debug_only"],
    )
    vectors = [
        FlowVector(
            track_id=1,
            frame_index=34,
            timestamp_sec=1.1,
            x0=10,
            y0=20,
            x1=12,
            y1=21,
            dx=2,
            dy=1,
            magnitude=2.2,
            direction_deg=26.5,
        )
    ]
    comparison = {
        "oxts_relative_yaw": "1.0",
        "oxts_relative_pitch": "-0.2",
        "oxts_relative_roll": "0.0",
        "abs_yaw_error": "0.2",
        "abs_pitch_error": "0.2",
        "abs_roll_error": "0.1",
    }

    payload = _frame_payload(34, pose, vectors, comparison)

    assert payload["frame_index"] == 34
    assert payload["valid_track_count"] == 1
    assert payload["oxts_delta_yaw"] == 1.0
    assert payload["abs_pitch_error"] == 0.2
    assert "intrinsics_not_calibrated" in payload["warnings"]


def test_deep_dive_report_lists_worst_pitch_and_roll_frames() -> None:
    report = _render_deep_dive_report(
        [
            {"frame_index": 79, "abs_pitch_error": 8.8, "abs_roll_error": 0.2, "inlier_ratio": 0.6, "valid_track_count": 400},
            {"frame_index": 117, "abs_pitch_error": 1.0, "abs_roll_error": 15.3, "inlier_ratio": 0.7, "valid_track_count": 300},
        ]
    )

    assert "Pitch Worst" in report
    assert "Roll Worst" in report
    assert "frame 79" in report
    assert "frame 117" in report
    assert "approximate K sensitivity" in report


def test_prepare_dir_rejects_paths_outside_allowed_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"

    with pytest.raises(ValueError):
        _prepare_dir(outside, PROJECT_ROOT / "outputs")
