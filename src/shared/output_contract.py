from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import warnings

SCHEMA_VERSION = "1.0"
ROTATION_ORDER = "ZYX"
ANGLE_UNIT = "degree"
POSE_TIMELINE = "pose_timeline.csv"
FRAME_RESULTS = "frame_pose_results.json"
OVERLAY_VIDEO = "pose_overlay.mp4"
DEBUG_DIRECTORY = "debug_frames"
PER_FRAME = "per_frame.csv"
SUMMARY = "summary.json"
REPORT = "evaluation_report.md"
WORST_FRAMES = "worst_frames.csv"
PLOTS_DIRECTORY = "plots"

PipelineName = Literal["geometry", "optical"]


@dataclass(frozen=True)
class PipelineArtifacts:
    directory: Path

    @property
    def pose_timeline(self) -> Path:
        return self.directory / POSE_TIMELINE

    @property
    def frame_results(self) -> Path:
        return self.directory / FRAME_RESULTS

    @property
    def overlay_video(self) -> Path:
        return self.directory / OVERLAY_VIDEO

    @property
    def debug_frames(self) -> Path:
        return self.directory / DEBUG_DIRECTORY


@dataclass(frozen=True)
class EvaluationArtifacts:
    directory: Path

    @property
    def per_frame(self) -> Path:
        return self.directory / PER_FRAME

    @property
    def summary(self) -> Path:
        return self.directory / SUMMARY

    @property
    def report(self) -> Path:
        return self.directory / REPORT

    @property
    def worst_frames(self) -> Path:
        return self.directory / WORST_FRAMES

    @property
    def plots(self) -> Path:
        return self.directory / PLOTS_DIRECTORY


@dataclass(frozen=True)
class OutputContract:
    run_directory: Path

    def pipeline(self, pipeline: PipelineName) -> PipelineArtifacts:
        return PipelineArtifacts(self.run_directory / pipeline)

    def evaluation(self, pipeline: PipelineName) -> EvaluationArtifacts:
        return EvaluationArtifacts(self.run_directory / "eval" / pipeline)

    @property
    def geometry(self) -> PipelineArtifacts:
        return self.pipeline("geometry")

    @property
    def optical(self) -> PipelineArtifacts:
        return self.pipeline("optical")

    @property
    def geometry_evaluation(self) -> EvaluationArtifacts:
        return self.evaluation("geometry")

    @property
    def optical_evaluation(self) -> EvaluationArtifacts:
        return self.evaluation("optical")

    def selected(
        self,
        pipelines: tuple[PipelineName, ...] = (),
        evaluations: tuple[PipelineName, ...] = (),
    ) -> dict[str, PipelineArtifacts | EvaluationArtifacts]:
        return {
            **{pipeline: self.pipeline(pipeline) for pipeline in pipelines},
            **{
                f"eval/{pipeline}": self.evaluation(pipeline)
                for pipeline in evaluations
            },
        }


def resolve_legacy_artifact(path: Path, *legacy_names: str) -> Path:
    """Resolve the canonical name first, then an explicitly supported old sibling."""
    if path.exists():
        return path
    for name in legacy_names:
        legacy = path.with_name(name)
        if legacy.exists():
            warnings.warn(
                f"Legacy artifact name '{name}' is deprecated; use '{path.name}'.",
                DeprecationWarning,
                stacklevel=2,
            )
            return legacy
    return path


def validate_rotation_contract(metadata: dict[str, Any]) -> None:
    """Validate supplied metadata while allowing legacy records with no contract fields."""
    rotation_order = metadata.get("rotation_order")
    unit = metadata.get("unit")
    if rotation_order not in (None, "", ROTATION_ORDER):
        raise ValueError(f"rotation_order must be {ROTATION_ORDER}.")
    if unit not in (None, "", ANGLE_UNIT):
        raise ValueError(f"unit must be {ANGLE_UNIT}.")


def pose_metadata(
    pipeline: PipelineName,
    *,
    calibrated_heading: bool = False,
    intrinsics_calibrated: bool = False,
    intrinsics_source: str | None = None,
) -> dict[str, Any]:
    if pipeline == "geometry":
        return {
            "schema_version": SCHEMA_VERSION,
            "pipeline": pipeline,
            "pose_type": "absolute_orientation" if calibrated_heading else "single_frame_orientation",
            "reference_frame": "oxts_world" if calibrated_heading else "camera_image_geometry",
            "rotation_order": ROTATION_ORDER,
            "unit": ANGLE_UNIT,
            "comparison_ready": calibrated_heading,
            "calibrated_heading": calibrated_heading,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline": pipeline,
        "pose_type": "frame_to_frame_relative_rotation",
        "reference_frame": "camera",
        "rotation_order": ROTATION_ORDER,
        "unit": ANGLE_UNIT,
        "intrinsics_calibrated": intrinsics_calibrated,
        "intrinsics_source": intrinsics_source
        or ("calibrated_file" if intrinsics_calibrated else "approximate_from_image_size"),
    }
