from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.shared.output_contract import OutputContract, pose_metadata
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService, write_run_manifest
from src.app.evaluation.output_directory import resolve_evaluation_output_directory


def test_repository_paths_discover_from_nested_path() -> None:
    paths = RepositoryPaths.discover(Path("src/app"))

    assert paths.root.name == "camera-angle"
    assert paths.sample_images == paths.root / "data/samples/kitti/images"
    assert paths.sample_oxts == paths.root / "data/samples/kitti/references/oxts"
    assert "GIGABYTE" not in str(paths.sample_images.relative_to(paths.root))


def test_run_directory_is_collision_safe_and_side_effect_free(tmp_path: Path) -> None:
    clock = lambda: datetime(2026, 6, 22, 9, 10, 11)
    service = RunDirectoryService(tmp_path, clock)

    first = service.next_run_path()
    assert first.name == "20260622_091011_000"
    assert not first.exists()
    first.mkdir()
    second = service.next_run_path()
    assert second.name == "20260622_091011_000_01"
    second.mkdir()
    assert service.next_run_path().name == "20260622_091011_000_02"


def test_output_contract_paths_and_pose_semantics(tmp_path: Path) -> None:
    contract = OutputContract(tmp_path / "run")

    assert contract.geometry.pose_timeline.name == "pose_timeline.csv"
    assert contract.geometry.frame_results.name == "frame_pose_results.json"
    assert contract.optical.overlay_video.name == "pose_overlay.mp4"
    assert contract.geometry_evaluation.per_frame.name == "per_frame.csv"
    assert contract.optical_evaluation.summary.name == "summary.json"
    assert not contract.run_directory.exists()
    assert set(contract.selected(("geometry",), ("optical",))) == {"geometry", "eval/optical"}

    geometry = pose_metadata("geometry")
    optical = pose_metadata("optical")
    assert geometry["pose_type"] == "single_frame_orientation"
    assert geometry["reference_frame"] == "camera_image_geometry"
    assert geometry["comparison_ready"] is False
    assert optical["pose_type"] == "frame_to_frame_relative_rotation"
    assert optical["intrinsics_source"] == "approximate_from_image_size"


def test_default_evaluation_output_layout_is_lazy_and_collision_safe(tmp_path: Path) -> None:
    paths = RepositoryPaths(tmp_path)
    clock = lambda: datetime(2026, 6, 22, 12, 13, 14)
    service = RunDirectoryService(paths.outputs_root, clock)

    first = resolve_evaluation_output_directory(
        "geometry", None, repository_paths=paths, run_directory_service=service
    )
    assert first == tmp_path / "outputs/20260622_121314_000/eval/geometry"
    assert not first.exists()
    assert not paths.outputs_root.exists()

    (paths.outputs_root / "20260622_121314_000").mkdir(parents=True)
    second = resolve_evaluation_output_directory(
        "optical", None, repository_paths=paths, run_directory_service=service
    )
    assert second == tmp_path / "outputs/20260622_121314_000_01/eval/optical"
    assert not second.exists()


def test_explicit_evaluation_output_directory_is_preserved(tmp_path: Path) -> None:
    explicit = tmp_path / "custom-evaluation"
    resolved = resolve_evaluation_output_directory("geometry", explicit)
    assert resolved == explicit
    assert not explicit.exists()


def test_run_id_milliseconds_atomic_reservation_and_manifest(tmp_path: Path) -> None:
    created_at = datetime(
        2026, 6, 22, 15, 30, 45, 123456,
        tzinfo=timezone(timedelta(hours=8)),
    )
    service = RunDirectoryService(tmp_path / "outputs", lambda: created_at)

    preview = service.preview_run_path()
    assert preview.name == "20260622_153045_123"
    assert not preview.exists()
    assert not service.output_root.exists()

    first = service.reserve_run_directory()
    second = service.reserve_run_directory()
    third = service.reserve_run_directory()
    assert first.path.name == "20260622_153045_123"
    assert second.path.name == "20260622_153045_123_01"
    assert third.path.name == "20260622_153045_123_02"
    assert len({first.path, second.path, third.path}) == 3

    manifest_path = write_run_manifest(
        first,
        repository_root=tmp_path,
        selected_tasks=["eval_geometry"],
        ground_truth_type="oxts",
        ground_truth_path=tmp_path / "oxts",
        artifacts={"eval_geometry": first.path / "eval/geometry"},
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "20260622_153045_123"
    assert manifest["created_at"] == "2026-06-22T15:30:45.123+08:00"
    assert manifest["selected_tasks"] == ["eval_geometry"]
    assert manifest["inputs"] == {"image": None, "video": None}
    assert manifest["ground_truth"]["type"] == "oxts"
    assert manifest["artifacts"]["optical"] is None


def test_atomic_reservation_gives_competitors_unique_directories(tmp_path: Path) -> None:
    created_at = datetime(2026, 6, 22, 1, 2, 3, 7000)
    service = RunDirectoryService(tmp_path / "outputs", lambda: created_at)

    with ThreadPoolExecutor(max_workers=4) as executor:
        reservations = list(
            executor.map(lambda _: service.reserve_run_directory(), range(8))
        )

    paths = [reservation.path for reservation in reservations]
    assert len(set(paths)) == 8
    assert all(path.is_dir() for path in paths)
    assert {path.name for path in paths} == {
        "20260622_010203_007",
        *{f"20260622_010203_007_{index:02d}" for index in range(1, 8)},
    }
