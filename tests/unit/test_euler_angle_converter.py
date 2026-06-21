from __future__ import annotations

import numpy as np

from src.contexts.pose_estimation.services.euler_angle_converter import (
    euler_zyx_to_rotation_matrix,
    rotation_matrix_to_euler_zyx,
)


def test_identity_rotation_outputs_zero_angles() -> None:
    angles = rotation_matrix_to_euler_zyx(np.eye(3))

    assert abs(angles.yaw_deg) < 1e-9
    assert abs(angles.pitch_deg) < 1e-9
    assert abs(angles.roll_deg) < 1e-9


def test_known_yaw_rotation_outputs_reasonable_direction() -> None:
    rotation = euler_zyx_to_rotation_matrix(yaw_deg=15.0)
    angles = rotation_matrix_to_euler_zyx(rotation)

    assert 14.9 <= angles.yaw_deg <= 15.1
    assert abs(angles.pitch_deg) < 1e-9
    assert abs(angles.roll_deg) < 1e-9

