from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.services.line_detector import LineDetectionConfig, detect_lines
from src.contexts.input.domain.frame import Frame
from src.contexts.input.services.image_loader import load_frame
from src.contexts.output.services.debug_visualizer import (
    write_line_debug,
    write_preprocessing_debug,
    write_roll_debug,
)
from src.contexts.pose_estimation.domain.pose_result import PoseResult
from src.contexts.pose_estimation.services.roll_estimator import estimate_roll
from src.contexts.preprocessing.domain.edge_map import EdgeMap
from src.contexts.preprocessing.domain.preprocess_config import PreprocessConfig
from src.contexts.preprocessing.domain.preprocessed_frame import PreprocessedFrame
from src.contexts.preprocessing.services.edge_detector import detect_edges
from src.contexts.preprocessing.services.preprocessor import preprocess_frame


STAGE = "stage_0_3_foundation_and_roll"


@dataclass(frozen=True)
class VisualPosePipelineResult:
    frame: Frame
    preprocessed_frame: PreprocessedFrame
    edge_map: EdgeMap
    line_features: LineFeatureSet
    pose_result: PoseResult

    def to_dict(self) -> dict[str, object]:
        data = self.pose_result.to_dict()
        data["line_features"] = self.line_features.to_dict()
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
        stage=STAGE,
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
