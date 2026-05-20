from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.horizon_feature_set import HorizonFeatureSet
from src.contexts.geometry_features.domain.vanishing_point_feature_set import VanishingPointFeatureSet
from src.contexts.geometry_features.services.horizon_detector import HorizonDetectionConfig, detect_horizon
from src.contexts.geometry_features.services.line_detector import LineDetectionConfig, detect_lines
from src.contexts.geometry_features.services.vanishing_point_detector import (
    VanishingPointDetectionConfig,
    detect_vanishing_point,
)
from src.contexts.input.domain.frame import Frame
from src.contexts.input.services.image_loader import load_frame
from src.contexts.output.services.debug_visualizer import (
    write_horizon_debug,
    write_line_debug,
    write_pose_overlay,
    write_preprocessing_debug,
    write_roll_debug,
    write_vanishing_point_debug,
)
from src.contexts.pose_estimation.domain.pose_result import PoseResult
from src.contexts.pose_estimation.services.pitch_estimator import estimate_pitch
from src.contexts.pose_estimation.services.pose_integrator import build_pose_result
from src.contexts.pose_estimation.services.roll_estimator import estimate_roll
from src.contexts.pose_estimation.services.yaw_estimator import estimate_yaw
from src.contexts.preprocessing.domain.edge_map import EdgeMap
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig
from src.contexts.preprocessing.domain.preprocessed_frame import PreprocessedFrame
from src.contexts.preprocessing.services.edge_detector import detect_edges
from src.contexts.preprocessing.services.preprocessor import preprocess_frame


STAGE_0_3 = "stage_0_3_foundation_and_roll"
STAGE_4_7 = "stage_4_7_pose_integration_and_debug"


@dataclass(frozen=True)
class VisualPosePipelineResult:
    frame: Frame
    preprocessed_frame: PreprocessedFrame
    edge_map: EdgeMap
    line_features: LineFeatureSet
    pose_result: PoseResult

    def to_dict(self) -> dict[str, object]:
        data = self.pose_result.to_dict()
        if self.pose_result.stage == STAGE_0_3:
            data.pop("angle_confidence", None)
        data["line_features"] = self.line_features.to_dict()
        return data


@dataclass(frozen=True)
class PoseIntegrationPipelineResult:
    frame: Frame
    preprocessed_frame: PreprocessedFrame
    edge_map: EdgeMap
    line_features: LineFeatureSet
    horizon_features: HorizonFeatureSet
    vanishing_point_features: VanishingPointFeatureSet
    pose_result: PoseResult

    def to_dict(self) -> dict[str, object]:
        data = self.pose_result.to_dict()
        data["line_features"] = self.line_features.to_dict()
        data["horizon_features"] = self.horizon_features.to_dict()
        data["vanishing_point_features"] = self.vanishing_point_features.to_dict()
        return data


def run_visual_pose_pipeline(
    image_path: Path,
    debug_dir: Path,
    preprocess_config: PreprocessConfig | None = None,
    line_config: LineDetectionConfig | None = None,
) -> VisualPosePipelineResult:
    preprocess_config = preprocess_config or PreprocessConfig()
    line_config = line_config or LineDetectionConfig()

    frame = load_frame(image_path)
    preprocessed = preprocess_frame(frame, preprocess_config)
    edge_map = detect_edges(preprocessed, preprocess_config)
    line_features = detect_lines(edge_map, line_config)
    roll_estimate = estimate_roll(line_features)

    debug_artifacts: dict[str, str] = {}
    debug_artifacts.update(write_preprocessing_debug(debug_dir, preprocessed, edge_map))
    debug_artifacts.update(write_line_debug(debug_dir, preprocessed, line_features))
    debug_artifacts.update(write_roll_debug(debug_dir, preprocessed, line_features, roll_estimate))

    warnings = []
    if roll_estimate.roll is None:
        warnings.append("Roll could not be estimated because no stable horizontal or vertical line candidates were found.")
    elif roll_estimate.confidence < 0.35:
        warnings.append("Roll confidence is low; the image may not contain enough stable structural lines.")

    pose_result = PoseResult(
        image=frame.filename,
        yaw=None,
        pitch=None,
        roll=roll_estimate.roll,
        unit=roll_estimate.unit,
        confidence=roll_estimate.confidence,
        method="geometry_based_partial_pose_estimation",
        stage=STAGE_0_3,
        features_used=["edges", "lines"],
        debug_artifacts=debug_artifacts,
        warnings=warnings,
    )
    return VisualPosePipelineResult(
        frame=frame,
        preprocessed_frame=preprocessed,
        edge_map=edge_map,
        line_features=line_features,
        pose_result=pose_result,
    )


def run_stage_4_7_pose_pipeline(
    image_path: Path,
    debug_dir: Path,
    preprocess_config: PreprocessConfig | None = None,
    line_config: LineDetectionConfig | None = None,
    horizon_config: HorizonDetectionConfig | None = None,
    vanishing_point_config: VanishingPointDetectionConfig | None = None,
) -> PoseIntegrationPipelineResult:
    preprocess_config = preprocess_config or PreprocessConfig()
    line_config = line_config or LineDetectionConfig()

    frame = load_frame(image_path)
    preprocessed = preprocess_frame(frame, preprocess_config)
    edge_map = detect_edges(preprocessed, preprocess_config)
    line_features = detect_lines(edge_map, line_config)
    horizon_features = detect_horizon(
        line_features,
        preprocessed.width,
        preprocessed.height,
        horizon_config,
    )
    vanishing_point_features = detect_vanishing_point(
        line_features,
        preprocessed.width,
        preprocessed.height,
        vanishing_point_config,
    )

    roll_estimate = estimate_roll(line_features)
    pitch_estimate = estimate_pitch(horizon_features, preprocessed.width, preprocessed.height)
    yaw_estimate = estimate_yaw(vanishing_point_features, preprocessed.width, preprocessed.height)

    warnings = _stage_4_7_warnings(roll_estimate, pitch_estimate, yaw_estimate)
    debug_artifacts: dict[str, str] = {}
    debug_artifacts.update(write_preprocessing_debug(debug_dir, preprocessed, edge_map))
    debug_artifacts.update(write_line_debug(debug_dir, preprocessed, line_features))
    debug_artifacts.update(write_roll_debug(debug_dir, preprocessed, line_features, roll_estimate))
    debug_artifacts.update(write_horizon_debug(debug_dir, preprocessed, horizon_features, pitch_estimate.pitch))
    debug_artifacts.update(
        write_vanishing_point_debug(
            debug_dir,
            preprocessed,
            vanishing_point_features,
            yaw_estimate.yaw,
        )
    )

    pose_result = build_pose_result(
        image=frame.filename,
        yaw=yaw_estimate,
        pitch=pitch_estimate,
        roll=roll_estimate,
        stage=STAGE_4_7,
        debug_artifacts=debug_artifacts,
        warnings=warnings,
    )
    debug_artifacts.update(write_pose_overlay(debug_dir, preprocessed, horizon_features, vanishing_point_features, pose_result))
    pose_result = build_pose_result(
        image=frame.filename,
        yaw=yaw_estimate,
        pitch=pitch_estimate,
        roll=roll_estimate,
        stage=STAGE_4_7,
        debug_artifacts=debug_artifacts,
        warnings=warnings,
    )

    return PoseIntegrationPipelineResult(
        frame=frame,
        preprocessed_frame=preprocessed,
        edge_map=edge_map,
        line_features=line_features,
        horizon_features=horizon_features,
        vanishing_point_features=vanishing_point_features,
        pose_result=pose_result,
    )


def _stage_4_7_warnings(roll_estimate, pitch_estimate, yaw_estimate) -> list[str]:
    warnings = []
    if roll_estimate.roll is None:
        warnings.append("Roll could not be estimated because no stable horizontal or vertical line candidates were found.")
    elif roll_estimate.confidence < 0.35:
        warnings.append("Roll confidence is low; the image may not contain enough stable structural lines.")

    if pitch_estimate.pitch is None:
        warnings.append(f"Pitch could not be estimated: {pitch_estimate.reason}.")
    elif pitch_estimate.confidence < 0.35:
        warnings.append("Pitch confidence is low; the horizon candidates may be unstable.")

    if yaw_estimate.yaw is None:
        warnings.append(f"Yaw could not be estimated: {yaw_estimate.reason}.")
    elif yaw_estimate.confidence < 0.35:
        warnings.append("Yaw confidence is low; the vanishing point candidates may be unstable.")
    return warnings
