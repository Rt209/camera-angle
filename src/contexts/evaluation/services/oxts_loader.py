from __future__ import annotations

import math
import re
from pathlib import Path

from src.contexts.evaluation.domain.pose_record import PoseAngles, ReferencePose


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def parse_pose_text(text: str, *, source: Path | None = None) -> PoseAngles | None:
    labelled = {
        key: float(value)
        for key, value in re.findall(
            r"\b(yaw_deg|pitch_deg|roll_deg)\s*:\s*([-+0-9.eE]+)", text
        )
    }
    if {"yaw_deg", "pitch_deg", "roll_deg"}.issubset(labelled):
        return PoseAngles(labelled["yaw_deg"], labelled["pitch_deg"], labelled["roll_deg"])

    values = text.strip().split()
    if not values:
        return None
    if len(values) < 6:
        where = f" in {source}" if source else ""
        raise ValueError(f"Malformed OXTS row{where}: expected at least 6 values, got {len(values)}")
    try:
        roll_rad, pitch_rad, yaw_rad = map(float, values[3:6])
    except ValueError as exc:
        where = f" in {source}" if source else ""
        raise ValueError(f"Malformed OXTS numeric value{where}: {exc}") from exc
    return PoseAngles(math.degrees(yaw_rad), math.degrees(pitch_rad), math.degrees(roll_rad))


def load_reference_poses(pose_path: Path) -> dict[int, ReferencePose]:
    pose_path = Path(pose_path)
    records: dict[int, ReferencePose] = {}
    if pose_path.is_dir():
        files = sorted(pose_path.glob("*.txt"), key=natural_key)
        if not files:
            raise ValueError(f"No OXTS txt files found in: {pose_path}")
        for path in files:
            if not path.stem.isdigit():
                raise ValueError(f"OXTS filename must be a numeric source frame index: {path.name}")
            frame_index = int(path.stem)
            pose = parse_pose_text(path.read_text(encoding="utf-8"), source=path)
            if pose is None:
                raise ValueError(f"Empty OXTS pose file: {path}")
            records[frame_index] = ReferencePose(pose.yaw_deg, pose.pitch_deg, pose.roll_deg, frame_index)
        return records
    if not pose_path.is_file():
        raise ValueError(f"Pose path does not exist: {pose_path}")
    text = pose_path.read_text(encoding="utf-8")
    if all(label in text for label in ("yaw_deg", "pitch_deg", "roll_deg")):
        pose = parse_pose_text(text, source=pose_path)
        if pose is not None:
            records[0] = ReferencePose(pose.yaw_deg, pose.pitch_deg, pose.roll_deg, 0)
        return records
    for frame_index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        pose = parse_pose_text(line, source=pose_path)
        if pose is not None:
            records[frame_index] = ReferencePose(pose.yaw_deg, pose.pitch_deg, pose.roll_deg, frame_index)
    return records


def require_reference(references: dict[int, ReferencePose], frame_index: int) -> ReferencePose:
    try:
        return references[frame_index]
    except KeyError as exc:
        raise ValueError(f"Missing OXTS reference for required source frame index {frame_index}.") from exc


def load_poses(pose_path: Path) -> list[PoseAngles]:
    """Compatibility API for video assembly; validates contiguous frame identities."""
    records = load_reference_poses(pose_path)
    if not records:
        return []
    expected = list(range(max(records) + 1))
    missing = [index for index in expected if index not in records]
    if missing:
        raise ValueError(f"Missing OXTS reference for required source frame index {missing[0]}.")
    return [records[index] for index in expected]
