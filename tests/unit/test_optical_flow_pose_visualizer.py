import numpy as np

from src.contexts.motion_analysis.domain.flow_track import FlowVector
from src.contexts.output.services.optical_flow_pose_visualizer import draw_uncalibrated_pose_overlay


def test_pose_overlay_does_not_draw_flow_vectors() -> None:
    frame = np.full((500, 1000, 3), 80, dtype=np.uint8)
    vector = FlowVector(
        track_id=1,
        frame_index=1,
        timestamp_sec=0.1,
        x0=750.0,
        y0=300.0,
        x1=850.0,
        y1=300.0,
        dx=100.0,
        dy=0.0,
        magnitude=100.0,
        direction_deg=0.0,
    )

    overlay = draw_uncalibrated_pose_overlay(frame, [vector], pose=None)

    assert np.array_equal(overlay[250:, :, :], frame[250:, :, :])
    assert not np.array_equal(overlay[:200, :, :], frame[:200, :, :])
