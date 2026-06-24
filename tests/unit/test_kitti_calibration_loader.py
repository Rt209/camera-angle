from pathlib import Path

import numpy as np

from src.app.optical_flow_pose_overlay_pipeline import (
    UncalibratedPoseOverlayConfig,
    UncalibratedPoseOverlayPipeline,
)
from src.app.pipeline import run_stage_4_7_pose_pipeline
from src.contexts.camera_model.services.kitti_calibration_loader import (
    load_kitti_calibration,
)


CALIBRATION = (
    Path(__file__).resolve().parents[2]
    / "data/samples/kitti/calibration/2011_09_26"
)


def test_kitti_image_03_calibration_loads_intrinsics_and_extrinsics() -> None:
    profile = load_kitti_calibration(CALIBRATION, "03")

    assert profile.camera_index == "03"
    assert (profile.intrinsics.image_width, profile.intrinsics.image_height) == (
        1242,
        375,
    )
    assert np.isclose(profile.intrinsics.fx, 721.5377)
    assert np.isclose(profile.intrinsics.fy, 721.5377)
    assert np.isclose(profile.intrinsics.cx, 609.5593)
    assert np.isclose(profile.intrinsics.cy, 172.8540)
    rotation = profile.extrinsics.camera_to_vehicle_rotation
    assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5)
    assert np.isclose(np.linalg.det(rotation), 1.0, atol=1e-5)
    assert profile.extrinsics.camera_frame == "kitti_rectified_camera_03"


def test_kitti_codec_one_row_crop_keeps_rectified_intrinsics() -> None:
    pipeline = UncalibratedPoseOverlayPipeline(
        UncalibratedPoseOverlayConfig(
            kitti_calibration_directory=CALIBRATION,
            kitti_camera_index="03",
        )
    )

    intrinsics = pipeline._resolve_intrinsics(1242, 374)

    assert intrinsics.source == "kitti_P_rect_03"
    assert intrinsics.warnings == []
    assert np.isclose(intrinsics.camera_matrix[0, 0], 721.5377)
    assert np.isclose(intrinsics.camera_matrix[1, 2], 172.8540)


def test_geometry_pipeline_accepts_kitti_image_03_intrinsics() -> None:
    repository = Path(__file__).resolve().parents[2]
    image = repository / "data/samples/kitti/images/0000000000.png"
    profile = load_kitti_calibration(CALIBRATION, "03")

    approximate = run_stage_4_7_pose_pipeline(image)
    calibrated = run_stage_4_7_pose_pipeline(
        image, camera_intrinsics=profile.intrinsics
    )

    assert calibrated.pose_result.pitch is not None
    assert calibrated.pose_result.yaw is not None
    assert calibrated.pose_result.pitch != approximate.pose_result.pitch
    assert calibrated.pose_result.yaw != approximate.pose_result.yaw
