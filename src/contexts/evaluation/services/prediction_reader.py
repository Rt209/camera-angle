from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.contexts.evaluation.domain.pose_record import PredictionRecord
from src.shared.output_contract import validate_rotation_contract


def read_geometry_predictions(path: Path) -> list[PredictionRecord]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return [_geometry_record(row, index) for index, row in enumerate(csv.DictReader(handle))]


def read_optical_predictions(path: Path) -> list[PredictionRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_optical_record(row, index) for index, row in enumerate(payload.get("frames", []))]


def _geometry_record(row: dict[str, Any], index: int) -> PredictionRecord:
    validate_rotation_contract(row)
    frame_index = int(row.get("source_frame_index") or row["frame_index"])
    yaw = _float(row.get("yaw_deg") or row.get("yaw"))
    pitch = _float(row.get("pitch_deg") or row.get("pitch"))
    roll = _float(row.get("roll_deg") or row.get("roll"))
    return PredictionRecord(
        sample_index=int(row.get("sample_index") or index),
        pipeline=row.get("pipeline") or "geometry",
        pose_type=row.get("pose_type") or "single_frame_orientation",
        rotation_order=row.get("rotation_order") or "ZYX",
        unit=row.get("unit") or "degree",
        confidence=_float(row.get("confidence")),
        warnings=_warnings(row.get("warnings")),
        prediction_valid=all(value is not None for value in (yaw, pitch, roll)),
        source_frame_index=frame_index,
        timestamp_sec=_float(row.get("timestamp_sec") or row.get("time_sec")),
        yaw_deg=yaw,
        pitch_deg=pitch,
        roll_deg=roll,
    )


def _optical_record(row: dict[str, Any], index: int) -> PredictionRecord:
    validate_rotation_contract(row)
    current = int(row.get("source_frame_index_curr") or row["frame_index"])
    previous = int(row.get("source_frame_index_prev") if row.get("source_frame_index_prev") is not None else current - 1)
    yaw = _float(row.get("yaw_deg"))
    pitch = _float(row.get("pitch_deg"))
    roll = _float(row.get("roll_deg"))
    return PredictionRecord(
        sample_index=int(row.get("sample_index") or index),
        pipeline=row.get("pipeline") or "optical",
        pose_type=row.get("pose_type") or "frame_to_frame_relative_rotation",
        rotation_order=row.get("rotation_order") or "ZYX",
        unit=row.get("unit") or "degree",
        confidence=_float(row.get("confidence")),
        warnings=_warnings(row.get("warnings")),
        prediction_valid=all(value is not None for value in (yaw, pitch, roll)),
        source_frame_index_prev=previous,
        source_frame_index_curr=current,
        timestamp_sec_prev=_float(row.get("timestamp_sec_prev")),
        timestamp_sec_curr=_float(row.get("timestamp_sec_curr") or row.get("timestamp_sec")),
        yaw_deg=yaw,
        pitch_deg=pitch,
        roll_deg=roll,
    )


def _float(value: Any) -> float | None:
    return None if value is None or value == "" else float(value)


def _warnings(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, str) and value.startswith("["):
        return tuple(json.loads(value))
    return tuple(part for part in str(value).split("|") if part)
