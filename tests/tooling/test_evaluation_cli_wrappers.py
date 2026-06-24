import subprocess
import sys
from pathlib import Path
from datetime import datetime

from tools.evaluation.evaluate_uncalibrated_pose_overlay_against_oxts import (
    PROJECT_ROOT as OPTICAL_ROOT,
    REPOSITORY_PATHS as OPTICAL_PATHS,
    build_parser as optical_parser,
)
from tools.evaluation.evaluate_video_pose_against_oxts import (
    PROJECT_ROOT as GEOMETRY_ROOT,
    REPOSITORY_PATHS as GEOMETRY_PATHS,
    build_parser as geometry_parser,
)
from src.app.evaluation.output_directory import resolve_evaluation_output_directory
from src.shared.run_directory import RunDirectoryService


def test_evaluation_wrapper_flags_and_theta_defaults_are_compatible() -> None:
    geometry = geometry_parser().parse_args([])
    optical = optical_parser().parse_args([])

    assert geometry.theta_deg == 3.0
    assert optical.theta_deg == 1.0
    assert geometry.output_dir is None
    assert optical.output_dir is None
    assert optical.kitti_camera_index == "03"
    assert optical.kitti_calibration_dir is None
    assert optical.camera_extrinsics is None
    assert geometry.pose_csv.is_absolute()
    assert optical.pose_json.is_absolute()
    assert geometry.oxts_dir == GEOMETRY_PATHS.sample_oxts
    assert optical.oxts_dir == OPTICAL_PATHS.sample_oxts
    for args in (geometry, optical):
        assert hasattr(args, "oxts_dir")
        assert hasattr(args, "output_dir")
        assert args.save_plots is False
        assert args.save_worst_frames is False


def test_evaluation_wrappers_help_runs_from_external_cwd(tmp_path: Path) -> None:
    scripts = [
        GEOMETRY_ROOT / "tools/evaluation/evaluate_video_pose_against_oxts.py",
        OPTICAL_ROOT / "tools/evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py",
    ]
    for script in scripts:
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert "--output-dir" in completed.stdout


def test_external_cwd_default_outputs_stay_under_wrapper_repository(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    clock = lambda: datetime(2099, 1, 2, 3, 4, 5)

    geometry = resolve_evaluation_output_directory(
        "geometry",
        None,
        repository_paths=GEOMETRY_PATHS,
        run_directory_service=RunDirectoryService(GEOMETRY_PATHS.outputs_root, clock),
    )
    optical = resolve_evaluation_output_directory(
        "optical",
        None,
        repository_paths=OPTICAL_PATHS,
        run_directory_service=RunDirectoryService(OPTICAL_PATHS.outputs_root, clock),
    )

    assert geometry == GEOMETRY_ROOT / "outputs/20990102_030405_000/eval/geometry"
    assert optical == OPTICAL_ROOT / "outputs/20990102_030405_000/eval/optical"
    assert not geometry.exists()
    assert not optical.exists()
    assert not (tmp_path / "outputs").exists()


def test_explicit_relative_paths_keep_cwd_semantics() -> None:
    geometry = geometry_parser().parse_args(
        ["--pose-csv", "relative.csv", "--oxts-dir", "relative-oxts", "--output-dir", "relative-output"]
    )
    assert geometry.pose_csv == Path("relative.csv")
    assert geometry.oxts_dir == Path("relative-oxts")
    assert geometry.output_dir == Path("relative-output")
