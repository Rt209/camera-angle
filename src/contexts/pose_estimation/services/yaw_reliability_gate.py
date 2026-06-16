from __future__ import annotations

import json
import math
from statistics import median
from typing import Any, Protocol


class VideoYawFrame(Protocol):
    pose_result: dict[str, Any]
    feature_metadata: dict[str, Any]
    warnings: list[str]


def apply_video_yaw_reliability(frame_results: list[VideoYawFrame], image_width: int) -> None:
    reference_sign = _reference_yaw_sign(frame_results)
    previous_vp: tuple[float, float] | None = None
    previous_side: int | None = None
    center_x = image_width / 2.0

    for result in frame_results:
        vp = _selected_vp(result.feature_metadata)
        raw_yaw = _as_float(result.pose_result.get("yaw"))
        original_yaw_confidence = _as_float((result.pose_result.get("angle_confidence") or {}).get("yaw"))
        cluster_ambiguity = _as_float(
            (result.feature_metadata.get("vanishing_point_features") or {}).get("cluster_ambiguity")
        )
        line_support_consistency = _as_float(
            (result.feature_metadata.get("vanishing_point_features") or {}).get("line_support_consistency")
        )
        temporal_jump = _vp_jump(vp, previous_vp)
        side = _vp_side(vp, center_x)
        frame_side_flip = previous_side is not None and side is not None and side != previous_side

        warning_flags = _yaw_warning_flags(
            raw_yaw=raw_yaw,
            reference_sign=reference_sign,
            temporal_jump=temporal_jump,
            frame_side_flip=frame_side_flip,
            cluster_ambiguity=cluster_ambiguity,
            line_support_consistency=line_support_consistency,
        )
        corrected_yaw = _correct_yaw_to_reference(raw_yaw, reference_sign, warning_flags)
        adjusted_confidence = _adjust_yaw_confidence(original_yaw_confidence, warning_flags)

        result.feature_metadata["yaw_reliability"] = {
            "raw_vp_yaw": raw_yaw,
            "image_geometry_yaw": raw_yaw,
            "calibrated_heading_yaw": None,
            "comparison_ready": False,
            "pose_semantics": "single_frame_vanishing_point_image_geometry_yaw",
            "vp_temporal_jump": temporal_jump,
            "vp_side_flip": "yaw_sign_reference_flip" in warning_flags or frame_side_flip,
            "vp_cluster_ambiguity": cluster_ambiguity,
            "line_support_consistency": line_support_consistency,
            "yaw_warning_flags": warning_flags,
        }

        if corrected_yaw is not None:
            result.pose_result["yaw"] = corrected_yaw
        if adjusted_confidence is not None:
            angle_confidence = dict(result.pose_result.get("angle_confidence") or {})
            angle_confidence["yaw"] = adjusted_confidence
            result.pose_result["angle_confidence"] = angle_confidence
            result.pose_result["confidence"] = _overall_confidence(angle_confidence)

        if warning_flags:
            result.warnings.append(f"Yaw reliability warning: {json.dumps(warning_flags, ensure_ascii=True)}")

        if vp[0] is not None and vp[1] is not None:
            previous_vp = (vp[0], vp[1])
        if side is not None:
            previous_side = side


def _reference_yaw_sign(frame_results: list[VideoYawFrame]) -> int | None:
    early_yaws = [
        yaw
        for result in frame_results[:15]
        if (yaw := _as_float(result.pose_result.get("yaw"))) is not None and abs(yaw) >= 1.0
    ]
    if not early_yaws:
        return None
    return -1 if median(early_yaws) < 0 else 1


def _yaw_warning_flags(
    raw_yaw: float | None,
    reference_sign: int | None,
    temporal_jump: float | None,
    frame_side_flip: bool,
    cluster_ambiguity: float | None,
    line_support_consistency: float | None,
) -> list[str]:
    flags: list[str] = []
    if raw_yaw is not None and reference_sign is not None and raw_yaw * reference_sign < 0:
        flags.append("yaw_sign_reference_flip")
    if frame_side_flip:
        flags.append("vp_side_flip")
    if temporal_jump is not None and temporal_jump >= 120.0:
        flags.append("large_temporal_jump")
    if cluster_ambiguity is not None and cluster_ambiguity >= 0.55:
        flags.append("high_cluster_ambiguity")
    if line_support_consistency is not None and line_support_consistency < 0.35:
        flags.append("low_line_support_consistency")
    return flags


def _correct_yaw_to_reference(raw_yaw: float | None, reference_sign: int | None, warning_flags: list[str]) -> float | None:
    if raw_yaw is None:
        return None
    if reference_sign is None:
        return raw_yaw
    if "yaw_sign_reference_flip" not in warning_flags:
        return raw_yaw
    return round(reference_sign * abs(raw_yaw), 2)


def _adjust_yaw_confidence(confidence: float | None, warning_flags: list[str]) -> float | None:
    if confidence is None:
        return None
    penalty = 0.0
    if "yaw_sign_reference_flip" in warning_flags:
        penalty += 0.20
    if "vp_side_flip" in warning_flags:
        penalty += 0.15
    if "large_temporal_jump" in warning_flags:
        penalty += 0.20
    if "high_cluster_ambiguity" in warning_flags:
        penalty += 0.25
    if "low_line_support_consistency" in warning_flags:
        penalty += 0.10
    return round(max(0.0, min(1.0, confidence * (1.0 - min(penalty, 0.85)))), 2)


def _overall_confidence(confidence_by_angle: dict[str, float]) -> float:
    valid = [float(value) for value in confidence_by_angle.values() if value is not None and float(value) > 0]
    if not valid:
        return 0.0
    return round(sum(valid) / len(valid), 2)


def _selected_vp(feature_metadata: dict[str, Any]) -> tuple[float | None, float | None]:
    vp = feature_metadata.get("vanishing_point_features") or {}
    selected = vp.get("selected_vanishing_point") or {}
    return _as_float(selected.get("x")), _as_float(selected.get("y"))


def _vp_jump(current: tuple[float | None, float | None], previous: tuple[float, float] | None) -> float | None:
    if previous is None or current[0] is None or current[1] is None:
        return None
    return math.hypot(current[0] - previous[0], current[1] - previous[1])


def _vp_side(vp: tuple[float | None, float | None], center_x: float) -> int | None:
    if vp[0] is None:
        return None
    return -1 if vp[0] < center_x else 1


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
