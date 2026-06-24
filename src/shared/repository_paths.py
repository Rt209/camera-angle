from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepositoryPaths:
    """Repository-owned paths without filesystem side effects."""

    root: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> "RepositoryPaths":
        candidate = (start or Path.cwd()).resolve()
        if candidate.is_file():
            candidate = candidate.parent
        for directory in (candidate, *candidate.parents):
            if (directory / "pyproject.toml").is_file():
                return cls(directory)
        raise FileNotFoundError(f"Could not find repository root from: {candidate}")

    @property
    def sample_root(self) -> Path:
        return self.root / "data" / "samples" / "kitti"

    @property
    def sample_images(self) -> Path:
        return self.sample_root / "images"

    @property
    def sample_videos(self) -> Path:
        return self.sample_root / "videos"

    @property
    def sample_references(self) -> Path:
        return self.sample_root / "references"

    @property
    def sample_oxts(self) -> Path:
        return self.sample_references / "oxts"

    @property
    def sample_calibration(self) -> Path:
        return self.sample_root / "calibration" / "2011_09_26"

    @property
    def sample_video(self) -> Path:
        return self.sample_videos / "kitti_no_overlay.mp4"

    @property
    def sample_overlay_video(self) -> Path:
        return self.sample_videos / "kitti_pose_overlay.mp4"

    @property
    def outputs_root(self) -> Path:
        return self.root / "outputs"
