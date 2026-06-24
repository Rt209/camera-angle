from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.contexts.evaluation.domain.evaluation_result import EvaluationOutputs
from src.contexts.evaluation.services.geometry_evaluator import (
    evaluate_rows,
    read_pose_timeline,
    run_evaluation,
    write_evaluation_outputs,
)
from src.contexts.evaluation.services.oxts_loader import load_poses
from src.app.evaluation.output_directory import reserve_evaluation_output_directory
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService, write_run_manifest
from src.shared.output_contract import ANGLE_UNIT, ROTATION_ORDER


@dataclass(frozen=True)
class GeometryEvaluationConfig:
    theta_deg: float = 3.0
    save_plots: bool = False
    save_worst_frames: bool = False
    rotation_order: str = ROTATION_ORDER
    unit: str = ANGLE_UNIT

    def __post_init__(self) -> None:
        if self.theta_deg <= 0:
            raise ValueError("theta_deg must be greater than zero.")
        if self.rotation_order != ROTATION_ORDER:
            raise ValueError(f"rotation_order must be {ROTATION_ORDER}.")
        if self.unit != ANGLE_UNIT:
            raise ValueError(f"unit must be {ANGLE_UNIT}.")


def evaluate_geometry_pose(
    pose_csv: Path,
    reference_dir: Path,
    output_dir: Path,
    config: GeometryEvaluationConfig | None = None,
) -> EvaluationOutputs:
    selected = config or GeometryEvaluationConfig()
    return run_evaluation(
        pose_csv,
        reference_dir,
        output_dir,
        theta_deg=selected.theta_deg,
        save_plots=selected.save_plots,
        save_worst_frames=selected.save_worst_frames,
    )


def evaluate_standalone_geometry_pose(
    pose_csv: Path,
    reference_dir: Path,
    repository_paths: RepositoryPaths,
    config: GeometryEvaluationConfig | None = None,
    *,
    run_directory_service: RunDirectoryService | None = None,
) -> EvaluationOutputs:
    selected = config or GeometryEvaluationConfig()
    rows = read_pose_timeline(pose_csv)
    references = load_poses(reference_dir)
    evaluated = evaluate_rows(rows, references)
    reserved = reserve_evaluation_output_directory(
        "geometry",
        repository_paths=repository_paths,
        run_directory_service=run_directory_service,
    )
    outputs = write_evaluation_outputs(
        evaluated,
        reserved.output_directory,
        theta_deg=selected.theta_deg,
        save_plots=selected.save_plots,
        save_worst_frames=selected.save_worst_frames,
    )
    write_run_manifest(
        reserved.run,
        repository_root=repository_paths.root,
        selected_tasks=["eval_geometry"],
        ground_truth_type="oxts",
        ground_truth_path=reference_dir,
        artifacts={"eval_geometry": reserved.output_directory},
    )
    return outputs
