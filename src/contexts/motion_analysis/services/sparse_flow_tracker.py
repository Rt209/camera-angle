from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.contexts.input.adapters.video_source import FrameSamplingConfig, SampledVideoFrame, VideoSource
from src.contexts.motion_analysis.domain.flow_track import FlowDebugFrame, FlowVector, SparseFlowResult
from src.contexts.motion_analysis.services.flow_statistics import summarize_flow_frame


@dataclass(frozen=True)
class ShiTomasiConfig:
    max_corners: int = 1000
    quality_level: float = 0.01
    min_distance: int = 8
    block_size: int = 7


@dataclass(frozen=True)
class LucasKanadeConfig:
    win_size: tuple[int, int] = (21, 21)
    max_level: int = 3
    criteria_count: int = 30
    criteria_eps: float = 0.01


@dataclass(frozen=True)
class SparseFlowTrackerConfig:
    feature: ShiTomasiConfig = ShiTomasiConfig()
    lk: LucasKanadeConfig = LucasKanadeConfig()
    frame_step: int = 1
    max_debug_frames: int = 120
    output_debug_every_n_frames: int = 10
    min_valid_tracks: int = 10
    redetect_below: int = 50
    max_path_length: int = 80


class SparseFlowTracker:
    def __init__(self, config: SparseFlowTrackerConfig | None = None) -> None:
        self.config = config or SparseFlowTrackerConfig()

    def track_video(self, video_path: Path) -> SparseFlowResult:
        source = VideoSource(video_path)
        sampled_frames = source.iter_sampled_frames(FrameSamplingConfig(sample_every=self.config.frame_step))
        return self.track_sampled_frames(
            sampled_frames=sampled_frames,
            video_path=str(video_path),
            fps=source.metadata.fps,
            image_width=source.metadata.width,
            image_height=source.metadata.height,
            max_frames=self.config.max_debug_frames,
        )

    def track_sampled_frames(
        self,
        sampled_frames: object,
        video_path: str,
        fps: float,
        image_width: int,
        image_height: int,
        max_frames: int | None = None,
    ) -> SparseFlowResult:
        iterator = iter(sampled_frames)
        try:
            first = next(iterator)
        except StopIteration:
            return SparseFlowResult(video_path, fps, image_width, image_height, 0, [], [], [], ["no_frames"])

        prev_gray = self._to_gray(first.frame.image_bgr)
        prev_points = self._detect_features(prev_gray)
        next_track_id = 0
        track_ids: list[int] = []
        paths: dict[int, list[tuple[float, float]]] = {}
        if prev_points is not None:
            for point in prev_points.reshape(-1, 2):
                track_ids.append(next_track_id)
                paths[next_track_id] = [(float(point[0]), float(point[1]))]
                next_track_id += 1

        summaries = []
        all_vectors: list[FlowVector] = []
        debug_frames: list[FlowDebugFrame] = []
        warnings: list[str] = []
        processed = 1

        for sampled in iterator:
            if max_frames is not None and processed >= max_frames:
                break
            processed += 1
            curr_gray = self._to_gray(sampled.frame.image_bgr)
            vectors: list[FlowVector] = []
            tracked_count = int(len(prev_points)) if prev_points is not None else 0

            if prev_points is not None and len(prev_points) > 0:
                curr_points, status, errors = cv2.calcOpticalFlowPyrLK(
                    prev_gray,
                    curr_gray,
                    prev_points,
                    None,
                    winSize=self.config.lk.win_size,
                    maxLevel=self.config.lk.max_level,
                    criteria=(
                        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                        self.config.lk.criteria_count,
                        self.config.lk.criteria_eps,
                    ),
                )
                if curr_points is not None and status is not None:
                    valid_mask = status.reshape(-1) == 1
                    prev_flat = prev_points.reshape(-1, 2)
                    curr_flat = curr_points.reshape(-1, 2)
                    err_flat = errors.reshape(-1) if errors is not None else np.full(len(prev_flat), np.nan)
                    new_points = []
                    new_track_ids = []
                    for index, valid in enumerate(valid_mask):
                        if not valid or not np.all(np.isfinite(curr_flat[index])):
                            continue
                        track_id = track_ids[index]
                        vector = self._flow_vector(
                            track_id,
                            sampled.frame_index,
                            sampled.time_sec,
                            prev_flat[index],
                            curr_flat[index],
                            float(err_flat[index]) if np.isfinite(err_flat[index]) else None,
                        )
                        vectors.append(vector)
                        new_points.append(curr_flat[index])
                        new_track_ids.append(track_id)
                        paths.setdefault(track_id, []).append((vector.x1, vector.y1))
                        paths[track_id] = paths[track_id][-self.config.max_path_length :]

                    prev_points = (
                        np.asarray(new_points, dtype=np.float32).reshape(-1, 1, 2) if new_points else None
                    )
                    track_ids = new_track_ids

            summary = summarize_flow_frame(
                frame_index=sampled.frame_index,
                timestamp_sec=sampled.time_sec,
                tracked_point_count=tracked_count,
                vectors=vectors,
                min_valid_tracks=self.config.min_valid_tracks,
            )
            summaries.append(summary)
            all_vectors.extend(vectors)

            if self._should_keep_debug_frame(sampled.frame_index):
                debug_frames.append(
                    FlowDebugFrame(
                        frame_index=sampled.frame_index,
                        timestamp_sec=sampled.time_sec,
                        image_bgr=sampled.frame.image_bgr.copy(),
                        flow_vectors=vectors,
                        paths={track_id: list(path) for track_id, path in paths.items()},
                        summary=summary,
                    )
                )

            if prev_points is None or len(prev_points) < self.config.redetect_below:
                redetected = self._detect_features(curr_gray)
                prev_points, track_ids, next_track_id = self._merge_redetected_features(
                    existing_points=prev_points,
                    existing_ids=track_ids,
                    redetected=redetected,
                    paths=paths,
                    next_track_id=next_track_id,
                )

            prev_gray = curr_gray

        if not summaries:
            warnings.append("not_enough_frames_for_flow")
        if any("too_few_feature_points" in summary.warnings for summary in summaries):
            warnings.append("too_few_feature_points")
        if any("too_few_valid_tracks" in summary.warnings for summary in summaries):
            warnings.append("too_few_valid_tracks")

        return SparseFlowResult(
            video_path=video_path,
            fps=fps,
            image_width=image_width,
            image_height=image_height,
            processed_frame_count=processed,
            frame_summaries=summaries,
            flow_vectors=all_vectors,
            debug_frames=debug_frames,
            warnings=sorted(set(warnings)),
        )

    def _detect_features(self, gray: np.ndarray) -> np.ndarray | None:
        return cv2.goodFeaturesToTrack(
            gray,
            maxCorners=self.config.feature.max_corners,
            qualityLevel=self.config.feature.quality_level,
            minDistance=self.config.feature.min_distance,
            blockSize=self.config.feature.block_size,
        )

    def _merge_redetected_features(
        self,
        existing_points: np.ndarray | None,
        existing_ids: list[int],
        redetected: np.ndarray | None,
        paths: dict[int, list[tuple[float, float]]],
        next_track_id: int,
    ) -> tuple[np.ndarray | None, list[int], int]:
        if redetected is None or len(redetected) == 0:
            return existing_points, existing_ids, next_track_id

        existing_flat = existing_points.reshape(-1, 2) if existing_points is not None and len(existing_points) else np.empty((0, 2))
        points = [point for point in existing_flat]
        ids = list(existing_ids)
        for candidate in redetected.reshape(-1, 2):
            if existing_flat.size and np.min(np.linalg.norm(existing_flat - candidate, axis=1)) < self.config.feature.min_distance:
                continue
            points.append(candidate)
            ids.append(next_track_id)
            paths[next_track_id] = [(float(candidate[0]), float(candidate[1]))]
            next_track_id += 1
            if len(points) >= self.config.feature.max_corners:
                break
        merged = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2) if points else None
        return merged, ids, next_track_id

    def _should_keep_debug_frame(self, frame_index: int) -> bool:
        every = max(1, self.config.output_debug_every_n_frames)
        return frame_index % every == 0

    @staticmethod
    def _to_gray(image_bgr: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _flow_vector(
        track_id: int,
        frame_index: int,
        timestamp_sec: float,
        start: np.ndarray,
        end: np.ndarray,
        lk_error: float | None,
    ) -> FlowVector:
        dx = float(end[0] - start[0])
        dy = float(end[1] - start[1])
        magnitude = math.hypot(dx, dy)
        direction = math.degrees(math.atan2(dy, dx))
        return FlowVector(
            track_id=track_id,
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            x0=float(start[0]),
            y0=float(start[1]),
            x1=float(end[0]),
            y1=float(end[1]),
            dx=dx,
            dy=dy,
            magnitude=magnitude,
            direction_deg=direction,
            lk_error=lk_error,
        )

