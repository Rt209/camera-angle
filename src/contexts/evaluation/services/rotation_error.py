from __future__ import annotations

import math

import numpy as np

from src.contexts.pose_estimation.services.euler_angle_converter import (
    rotation_matrix_to_euler_zyx,
)


def signed_angle_error(predicted: float | None, expected: float) -> float | None:
    if predicted is None:
        return None
    return ((predicted - expected + 180.0) % 360.0) - 180.0


def angle_delta(current: float, previous: float) -> float:
    return ((current - previous + 180.0) % 360.0) - 180.0


def zyx_rotation_matrix(yaw_deg: float, pitch_deg: float, roll_deg: float) -> np.ndarray:
    yaw, pitch, roll = np.radians([yaw_deg, pitch_deg, roll_deg])
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=float,
    )


def geodesic_error_deg(
    predicted_ypr: tuple[float, float, float],
    expected_ypr: tuple[float, float, float],
) -> float:
    relative = zyx_rotation_matrix(*predicted_ypr) @ zyx_rotation_matrix(*expected_ypr).T
    cosine = float(np.clip((np.trace(relative) - 1.0) / 2.0, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def relative_rotation_zyx(
    previous_ypr: tuple[float, float, float],
    current_ypr: tuple[float, float, float],
) -> np.ndarray:
    """Return R_prev.T @ R_curr for active ZYX body orientations in world."""
    previous = zyx_rotation_matrix(*previous_ypr)
    current = zyx_rotation_matrix(*current_ypr)
    return previous.T @ current


def camera_motion_relative_rotation_zyx(
    previous_ypr: tuple[float, float, float],
    current_ypr: tuple[float, float, float],
) -> np.ndarray:
    """Return the previous-camera to current-camera rotation.

    OXTS ZYX matrices describe body orientation in the world. OpenCV
    recoverPose returns the change of coordinates from camera 1 to camera 2,
    whose rotation counterpart is R_world_current.T @ R_world_previous.
    """
    previous = zyx_rotation_matrix(*previous_ypr)
    current = zyx_rotation_matrix(*current_ypr)
    return current.T @ previous


def conjugate_vehicle_delta_to_camera(
    vehicle_delta: np.ndarray,
    camera_to_vehicle_rotation: np.ndarray,
) -> np.ndarray:
    """Convert a vehicle-frame delta using R_vc: R_c = R_vc.T R_v R_vc."""
    delta = np.asarray(vehicle_delta, dtype=np.float64)
    r_vehicle_camera = np.asarray(camera_to_vehicle_rotation, dtype=np.float64)
    if delta.shape != (3, 3) or r_vehicle_camera.shape != (3, 3):
        raise ValueError("rotation matrices must have shape (3, 3).")
    return r_vehicle_camera.T @ delta @ r_vehicle_camera


def rotation_matrix_to_pose_angles(rotation: np.ndarray) -> tuple[float, float, float]:
    angles = rotation_matrix_to_euler_zyx(rotation)
    return angles.yaw_deg, angles.pitch_deg, angles.roll_deg
