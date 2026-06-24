from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ReservedRunDirectory:
    path: Path
    run_id: str
    created_at: datetime


class RunDirectoryService:
    """Previews or atomically reserves collision-safe repository run directories."""

    def __init__(self, output_root: Path, clock: Callable[[], datetime] | None = None) -> None:
        self.output_root = Path(output_root)
        self.clock = clock or (lambda: datetime.now().astimezone())

    def preview_run_path(self) -> Path:
        run_id, _ = self._base_run()
        candidate = self.output_root / run_id
        suffix = 0
        while candidate.exists():
            suffix += 1
            candidate = self.output_root / f"{run_id}_{suffix:02d}"
        return candidate

    def reserve_run_directory(self) -> ReservedRunDirectory:
        run_id, created_at = self._base_run()
        self.output_root.mkdir(parents=True, exist_ok=True)
        suffix = 0
        while True:
            selected_id = run_id if suffix == 0 else f"{run_id}_{suffix:02d}"
            candidate = self.output_root / selected_id
            try:
                candidate.mkdir(exist_ok=False)
                return ReservedRunDirectory(candidate, selected_id, created_at)
            except FileExistsError:
                suffix += 1

    def next_run_path(self) -> Path:
        """Backward-compatible side-effect-free preview."""
        return self.preview_run_path()

    def path_for_run(self) -> Path:
        return self.preview_run_path()

    def _base_run(self) -> tuple[str, datetime]:
        created_at = self.clock()
        if created_at.tzinfo is None:
            created_at = created_at.astimezone()
        milliseconds = created_at.microsecond // 1000
        return f"{created_at.strftime('%Y%m%d_%H%M%S')}_{milliseconds:03d}", created_at


def write_run_manifest(
    reservation: ReservedRunDirectory,
    *,
    repository_root: Path,
    selected_tasks: list[str],
    inputs: dict[str, Path | None] | None = None,
    ground_truth_type: str | None = None,
    ground_truth_path: Path | None = None,
    artifacts: dict[str, Path | None] | None = None,
) -> Path:
    payload = {
        "schema_version": "1.0",
        "run_id": reservation.run_id,
        "created_at": reservation.created_at.isoformat(timespec="milliseconds"),
        "repository_root": str(Path(repository_root)),
        "selected_tasks": list(selected_tasks),
        "inputs": {
            "image": _path_or_none((inputs or {}).get("image")),
            "video": _path_or_none((inputs or {}).get("video")),
        },
        "ground_truth": {
            "type": ground_truth_type,
            "path": _path_or_none(ground_truth_path),
        },
        "artifacts": {
            "geometry": _path_or_none((artifacts or {}).get("geometry")),
            "optical": _path_or_none((artifacts or {}).get("optical")),
            "eval_geometry": _path_or_none((artifacts or {}).get("eval_geometry")),
            "eval_optical": _path_or_none((artifacts or {}).get("eval_optical")),
        },
    }
    path = reservation.path / "run_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _path_or_none(path: Path | None) -> str | None:
    return str(Path(path)) if path is not None else None
