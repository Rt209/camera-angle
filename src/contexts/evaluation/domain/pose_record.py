from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PoseAngles:
    yaw_deg: float
    pitch_deg: float
    roll_deg: float


@dataclass(frozen=True)
class ReferencePose(PoseAngles):
    source_frame_index: int


@dataclass(frozen=True)
class PredictionRecord:
    sample_index: int
    pipeline: str
    pose_type: str
    rotation_order: str = "ZYX"
    unit: str = "degree"
    confidence: float | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    prediction_valid: bool = False
    source_frame_index: int | None = None
    timestamp_sec: float | None = None
    source_frame_index_prev: int | None = None
    source_frame_index_curr: int | None = None
    timestamp_sec_prev: float | None = None
    timestamp_sec_curr: float | None = None
    yaw_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None
