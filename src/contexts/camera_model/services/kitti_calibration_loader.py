from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.contexts.camera_model.domain.extrinsics import CameraExtrinsics
from src.contexts.camera_model.domain.intrinsics import CameraIntrinsics


@dataclass(frozen=True)
class KittiCalibrationProfile:
    camera_index: str
    intrinsics: CameraIntrinsics
    extrinsics: CameraExtrinsics
    calibration_directory: Path


def load_kitti_calibration(
    calibration_directory: Path, camera_index: str = "03"
) -> KittiCalibrationProfile:
    directory = Path(calibration_directory)
    index = _normalize_camera_index(camera_index)
    camera = _read_calibration_file(directory / "calib_cam_to_cam.txt")
    velo_to_cam = _read_calibration_file(directory / "calib_velo_to_cam.txt")
    imu_to_velo = _read_calibration_file(directory / "calib_imu_to_velo.txt")

    projection = _matrix(camera, f"P_rect_{index}", 3, 4)
    rectified_size = _vector(camera, f"S_rect_{index}", 2)
    intrinsics = CameraIntrinsics(
        camera_matrix=projection[:, :3],
        dist_coeffs=np.zeros((5, 1), dtype=np.float64),
        image_width=int(round(rectified_size[0])),
        image_height=int(round(rectified_size[1])),
    )

    # KITTI projects IMU -> Velodyne -> unrectified camera 0 -> common
    # rectified camera coordinates. Rectified camera streams share this
    # orientation; P_rect_0X contributes the camera baseline translation.
    vehicle_to_camera = (
        _matrix(camera, "R_rect_00", 3, 3)
        @ _matrix(velo_to_cam, "R", 3, 3)
        @ _matrix(imu_to_velo, "R", 3, 3)
    )
    extrinsics = CameraExtrinsics(
        camera_to_vehicle_rotation=vehicle_to_camera.T,
        camera_frame=f"kitti_rectified_camera_{index}",
        source=f"kitti_raw:{directory.name}:image_{index}",
    )
    return KittiCalibrationProfile(index, intrinsics, extrinsics, directory)


def _normalize_camera_index(camera_index: str) -> str:
    value = str(camera_index).removeprefix("image_")
    if value not in {"00", "01", "02", "03"}:
        raise ValueError("KITTI camera index must be one of 00, 01, 02, or 03.")
    return value


def _read_calibration_file(path: Path) -> dict[str, list[float]]:
    if not path.is_file():
        raise FileNotFoundError(f"KITTI calibration file does not exist: {path}")
    values: dict[str, list[float]] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip() or ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        tokens = raw_value.split()
        if not tokens:
            continue
        try:
            values[key.strip()] = [float(token) for token in tokens]
        except ValueError:
            # calib_time is descriptive metadata rather than a numeric field.
            if key.strip() != "calib_time":
                raise ValueError(
                    f"Invalid numeric KITTI calibration field {key.strip()} "
                    f"at {path}:{line_number}."
                ) from None
    return values


def _vector(values: dict[str, list[float]], key: str, length: int) -> np.ndarray:
    if key not in values:
        raise ValueError(f"Missing KITTI calibration field: {key}")
    result = np.asarray(values[key], dtype=np.float64)
    if result.size != length:
        raise ValueError(f"KITTI field {key} must contain {length} values.")
    return result


def _matrix(
    values: dict[str, list[float]], key: str, rows: int, columns: int
) -> np.ndarray:
    return _vector(values, key, rows * columns).reshape(rows, columns)
