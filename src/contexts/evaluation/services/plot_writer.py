from pathlib import Path

from src.shared.output_contract import EvaluationArtifacts


def prepare_plots_directory(artifacts: EvaluationArtifacts) -> Path:
    artifacts.plots.mkdir(parents=True, exist_ok=True)
    return artifacts.plots
