from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CameraIntrinsics:
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    image_width: int
    image_height: int

    @property
    def fx(self) -> float:
        return float(self.camera_matrix[0, 0])

    @property
    def fy(self) -> float:
        return float(self.camera_matrix[1, 1])

    @property
    def cx(self) -> float:
        return float(self.camera_matrix[0, 2])

    @property
    def cy(self) -> float:
        return float(self.camera_matrix[1, 2])

    def to_dict(self) -> dict[str, object]:
        return {
            "image_width": self.image_width,
            "image_height": self.image_height,
            "camera_matrix": self.camera_matrix.astype(float).tolist(),
            "dist_coeffs": self.dist_coeffs.reshape(-1).astype(float).tolist(),
        }

    def camera_matrix_for_size(self, width: int, height: int) -> np.ndarray:
        """Adapt K for a proportional resize or a one-pixel codec edge crop."""
        if width <= 0 or height <= 0 or self.image_width <= 0 or self.image_height <= 0:
            raise ValueError("Camera intrinsics image sizes must be positive.")
        width_scale = width / self.image_width
        height_scale = height / self.image_height
        codec_edge_crop = width == self.image_width and abs(height - self.image_height) <= 1
        if not codec_edge_crop and abs(width_scale - height_scale) > 1e-3:
            raise ValueError("Camera intrinsics aspect ratio does not match the image.")
        matrix = self.camera_matrix.astype(np.float64).copy()
        if not codec_edge_crop:
            matrix[0, :] *= width_scale
            matrix[1, :] *= height_scale
        return matrix

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CameraIntrinsics":
        return cls(
            camera_matrix=np.asarray(data["camera_matrix"], dtype=np.float64),
            dist_coeffs=np.asarray(data["dist_coeffs"], dtype=np.float64).reshape(-1, 1),
            image_width=int(data["image_width"]),
            image_height=int(data["image_height"]),
        )


def load_camera_intrinsics(path: Path) -> CameraIntrinsics:
    import json

    return CameraIntrinsics.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
