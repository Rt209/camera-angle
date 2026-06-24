from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np


@dataclass(frozen=True)
class CameraExtrinsics:
    """Rotation from a rectified camera frame into the vehicle/IMU frame."""

    camera_to_vehicle_rotation: np.ndarray
    camera_frame: str
    vehicle_frame: str = "imu_vehicle"
    source: str = "calibration_file"

    def __post_init__(self) -> None:
        rotation = np.asarray(self.camera_to_vehicle_rotation, dtype=np.float64)
        if rotation.shape != (3, 3):
            raise ValueError("camera_to_vehicle_rotation must have shape (3, 3).")
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5):
            raise ValueError("camera_to_vehicle_rotation must be orthonormal.")
        if not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-5):
            raise ValueError("camera_to_vehicle_rotation must have determinant +1.")
        object.__setattr__(self, "camera_to_vehicle_rotation", rotation)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "camera_frame": self.camera_frame,
            "vehicle_frame": self.vehicle_frame,
            "source": self.source,
            "camera_to_vehicle_rotation": self.camera_to_vehicle_rotation.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CameraExtrinsics":
        return cls(
            camera_to_vehicle_rotation=np.asarray(
                data["camera_to_vehicle_rotation"], dtype=np.float64
            ),
            camera_frame=str(data["camera_frame"]),
            vehicle_frame=str(data.get("vehicle_frame") or "imu_vehicle"),
            source=str(data.get("source") or "calibration_file"),
        )


def load_camera_extrinsics(path: Path) -> CameraExtrinsics:
    return CameraExtrinsics.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
