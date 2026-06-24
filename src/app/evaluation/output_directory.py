from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

from src.shared.output_contract import OutputContract, PipelineName
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import ReservedRunDirectory, RunDirectoryService


@dataclass(frozen=True)
class ReservedEvaluationDirectory:
    output_directory: Path
    run: ReservedRunDirectory


def resolve_evaluation_output_directory(
    pipeline: PipelineName,
    explicit_output_dir: Path | None,
    *,
    repository_paths: RepositoryPaths | None = None,
    run_directory_service: RunDirectoryService | None = None,
) -> Path:
    """Resolve an evaluation directory without creating it."""
    if explicit_output_dir is not None:
        return Path(explicit_output_dir)
    paths = repository_paths or RepositoryPaths.discover()
    service = run_directory_service or RunDirectoryService(paths.outputs_root)
    return OutputContract(service.next_run_path()).evaluation(pipeline).directory


def reserve_evaluation_output_directory(
    pipeline: PipelineName,
    *,
    repository_paths: RepositoryPaths,
    run_directory_service: RunDirectoryService | None = None,
) -> ReservedEvaluationDirectory:
    service = run_directory_service or RunDirectoryService(repository_paths.outputs_root)
    reservation = service.reserve_run_directory()
    output_directory = OutputContract(reservation.path).evaluation(pipeline).directory
    return ReservedEvaluationDirectory(output_directory, reservation)
