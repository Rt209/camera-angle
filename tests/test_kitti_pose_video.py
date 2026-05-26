from pathlib import Path

from tools.kitti_pose_video import list_images, load_poses, parse_pose_text


def test_parse_kitti_oxts_pose_radians_to_degrees() -> None:
    text = (
        "49.011212804408 8.4228850417969 112.83492279053 "
        "0.022447 1e-05 -1.2219096732051 0 0 0"
    )

    pose = parse_pose_text(text)

    assert pose is not None
    assert round(pose.yaw_deg, 3) == -70.010
    assert round(pose.pitch_deg, 6) == 0.000573
    assert round(pose.roll_deg, 3) == 1.286


def test_parse_labelled_degrees_block() -> None:
    pose = parse_pose_text(
        """
        yaw_pitch_roll_degree:
          yaw_deg: -70.010
          pitch_deg: 0.000573
          roll_deg: 1.286
        """
    )

    assert pose is not None
    assert pose.yaw_deg == -70.010
    assert pose.pitch_deg == 0.000573
    assert pose.roll_deg == 1.286


def test_load_multiline_pose_file(tmp_path: Path) -> None:
    pose_file = tmp_path / "poses.txt"
    pose_file.write_text(
        "\n".join(
            [
                "0 0 0 0.0 0.0 0.0",
                "0 0 0 0.1 0.2 0.3",
            ]
        ),
        encoding="utf-8",
    )

    poses = load_poses(pose_file)

    assert len(poses) == 2
    assert round(poses[1].yaw_deg, 3) == 17.189


def test_list_images_uses_natural_sort(tmp_path: Path) -> None:
    for name in ["10.png", "2.png", "1.png"]:
        (tmp_path / name).write_bytes(b"")

    assert [path.name for path in list_images(tmp_path)] == ["1.png", "2.png", "10.png"]
