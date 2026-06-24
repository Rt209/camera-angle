from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.contexts.evaluation.domain.evaluation_result import EvaluationOutputs
from src.contexts.evaluation.services.optical_flow_evaluator import (
    evaluate_rows,
    read_pose_json,
    read_pose_metadata,
    run_evaluation,
    write_evaluation_outputs,
)
from src.contexts.evaluation.services.oxts_loader import load_poses
from src.app.evaluation.output_directory import reserve_evaluation_output_directory
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService, write_run_manifest
from src.shared.output_contract import ANGLE_UNIT, ROTATION_ORDER


@dataclass(frozen=True)
class OpticalFlowEvaluationConfig:
    theta_deg: float = 1.0
    save_plots: bool = False
    save_worst_frames: bool = False
    rotation_order: str = ROTATION_ORDER
    unit: str = ANGLE_UNIT
    camera_to_vehicle_rotation: np.ndarray | None = None
    extrinsics_source: str | None = None

    def __post_init__(self) -> None:
        if self.theta_deg <= 0:
            raise ValueError("theta_deg must be greater than zero.")
        if self.rotation_order != ROTATION_ORDER:
            raise ValueError(f"rotation_order must be {ROTATION_ORDER}.")
        if self.unit != ANGLE_UNIT:
            raise ValueError(f"unit must be {ANGLE_UNIT}.")
        if self.camera_to_vehicle_rotation is not None:
            rotation = np.asarray(self.camera_to_vehicle_rotation, dtype=np.float64)
            if rotation.shape != (3, 3):
                raise ValueError("camera_to_vehicle_rotation must have shape (3, 3).")
            object.__setattr__(self, "camera_to_vehicle_rotation", rotation)


def evaluate_optical_flow_pose(
    pose_json: Path,
    reference_dir: Path,
    output_dir: Path,
    config: OpticalFlowEvaluationConfig | None = None,
) -> EvaluationOutputs:
    selected = config or OpticalFlowEvaluationConfig()
    return run_evaluation(
        pose_json,
        reference_dir,
        output_dir,
        theta_deg=selected.theta_deg,
        save_plots=selected.save_plots,
        save_worst_frames=selected.save_worst_frames,
        camera_to_vehicle_rotation=selected.camera_to_vehicle_rotation,
        extrinsics_source=selected.extrinsics_source,
    )


def evaluate_standalone_optical_flow_pose(
    pose_json: Path,
    reference_dir: Path,
    repository_paths: RepositoryPaths,
    config: OpticalFlowEvaluationConfig | None = None,
    *,
    run_directory_service: RunDirectoryService | None = None,
) -> EvaluationOutputs:
    selected = config or OpticalFlowEvaluationConfig()
    rows = read_pose_json(pose_json)
    metadata = read_pose_metadata(pose_json)
    references = load_poses(reference_dir)
    comparison = evaluate_rows(
        rows, references, selected.camera_to_vehicle_rotation
    )
    reserved = reserve_evaluation_output_directory(
        "optical",
        repository_paths=repository_paths,
        run_directory_service=run_directory_service,
    )
    directory = reserved.output_directory
    outputs = write_evaluation_outputs(
        comparison,
        directory,
        theta_deg=selected.theta_deg,
        save_plots=selected.save_plots,
        save_worst_frames=selected.save_worst_frames,
        extrinsics_applied=selected.camera_to_vehicle_rotation is not None,
        intrinsics_calibrated=bool(metadata.get("intrinsics_calibrated")),
        extrinsics_source=selected.extrinsics_source,
    )
    write_run_manifest(
        reserved.run,
        repository_root=repository_paths.root,
        selected_tasks=["eval_optical"],
        ground_truth_type="oxts",
        ground_truth_path=reference_dir,
        artifacts={"eval_optical": directory},
    )
    return outputs
