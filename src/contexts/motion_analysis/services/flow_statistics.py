from __future__ import annotations

import math

import numpy as np

from src.contexts.motion_analysis.domain.flow_track import FlowFrameSummary, FlowVector


def summarize_flow_frame(
    frame_index: int,
    timestamp_sec: float,
    tracked_point_count: int,
    vectors: list[FlowVector],
    min_valid_tracks: int = 10,
) -> FlowFrameSummary:
    warnings: list[str] = []
    if tracked_point_count == 0:
        warnings.append("too_few_feature_points")
    if len(vectors) < min_valid_tracks:
        warnings.append("too_few_valid_tracks")

    if not vectors:
        return FlowFrameSummary(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            tracked_point_count=tracked_point_count,
            valid_track_count=0,
            mean_flow_magnitude=0.0,
            median_flow_magnitude=0.0,
            max_flow_magnitude=0.0,
            dominant_direction_deg=None,
            warnings=warnings,
        )

    magnitudes = np.asarray([vector.magnitude for vector in vectors], dtype=np.float64)
    directions = np.deg2rad(np.asarray([vector.direction_deg for vector in vectors], dtype=np.float64))
    mean_sin = float(np.mean(np.sin(directions)))
    mean_cos = float(np.mean(np.cos(directions)))
    dominant = math.degrees(math.atan2(mean_sin, mean_cos))
    return FlowFrameSummary(
        frame_index=frame_index,
        timestamp_sec=timestamp_sec,
        tracked_point_count=tracked_point_count,
        valid_track_count=len(vectors),
        mean_flow_magnitude=float(np.mean(magnitudes)),
        median_flow_magnitude=float(np.median(magnitudes)),
        max_flow_magnitude=float(np.max(magnitudes)),
        dominant_direction_deg=dominant,
        warnings=warnings,
    )

