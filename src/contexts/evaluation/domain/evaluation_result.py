from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvaluationConfig:
    pipeline: str
    theta_deg: float
    save_plots: bool = False
    save_worst_frames: bool = False
    rotation_order: str = "ZYX"
    unit: str = "degree"

    def __post_init__(self) -> None:
        if self.theta_deg <= 0:
            raise ValueError("theta_deg must be greater than zero.")


@dataclass(frozen=True)
class EvaluationOutputs:
    comparison_csv: Path
    summary_json: Path
    report_md: Path
    worst_frames_csv: Path | None = None
    plot_paths: dict[str, Path] = field(default_factory=dict)
