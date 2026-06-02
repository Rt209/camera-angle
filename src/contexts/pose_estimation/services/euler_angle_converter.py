from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EulerAngles:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    rotation_order: str = "ZYX"
    unit: str = "degree"

    def to_dict(self) -> dict[str, object]:
        return {
            "yaw_deg": self.yaw_deg,
            "pitch_deg": self.pitch_deg,
            "roll_deg": self.roll_deg,
            "rotation_order": self.rotation_order,
            "unit": self.unit,
        }


def rotation_matrix_to_euler_zyx(rotation_matrix: np.ndarray) -> EulerAngles:
    r = np.asarray(rotation_matrix, dtype=np.float64)
    if r.shape != (3, 3):
        raise ValueError("rotation_matrix must have shape (3, 3).")

    yaw = math.atan2(r[1, 0], r[0, 0])
    pitch = math.atan2(-r[2, 0], math.sqrt(r[2, 1] * r[2, 1] + r[2, 2] * r[2, 2]))
    roll = math.atan2(r[2, 1], r[2, 2])
    return EulerAngles(
        yaw_deg=math.degrees(yaw),
        pitch_deg=math.degrees(pitch),
        roll_deg=math.degrees(roll),
    )


def euler_zyx_to_rotation_matrix(yaw_deg: float = 0.0, pitch_deg: float = 0.0, roll_deg: float = 0.0) -> np.ndarray:
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    rz = np.array(
        [[math.cos(yaw), -math.sin(yaw), 0.0], [math.sin(yaw), math.cos(yaw), 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    ry = np.array(
        [[math.cos(pitch), 0.0, math.sin(pitch)], [0.0, 1.0, 0.0], [-math.sin(pitch), 0.0, math.cos(pitch)]],
        dtype=np.float64,
    )
    rx = np.array(
        [[1.0, 0.0, 0.0], [0.0, math.cos(roll), -math.sin(roll)], [0.0, math.sin(roll), math.cos(roll)]],
        dtype=np.float64,
    )
    return rz @ ry @ rx

