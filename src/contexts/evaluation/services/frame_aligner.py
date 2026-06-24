from __future__ import annotations

from src.contexts.evaluation.domain.aligned_pose import AlignedPosePair
from src.contexts.evaluation.domain.pose_record import PredictionRecord, ReferencePose
from src.contexts.evaluation.services.oxts_loader import require_reference


def align_geometry_prediction(
    prediction: PredictionRecord,
    references: dict[int, ReferencePose],
) -> AlignedPosePair:
    if prediction.source_frame_index is None:
        raise ValueError("Geometry prediction is missing source_frame_index.")
    return AlignedPosePair(
        prediction,
        require_reference(references, prediction.source_frame_index),
        None,
        "geometry_pose_vs_oxts_absolute_pose",
    )


def align_optical_prediction(
    prediction: PredictionRecord,
    references: dict[int, ReferencePose],
) -> AlignedPosePair:
    if prediction.source_frame_index_prev is None or prediction.source_frame_index_curr is None:
        raise ValueError("Optical prediction is missing prev/curr source frame identity.")
    return AlignedPosePair(
        prediction,
        require_reference(references, prediction.source_frame_index_curr),
        require_reference(references, prediction.source_frame_index_prev),
        "predicted_frame_to_frame_relative_rotation_vs_oxts_frame_to_frame_delta",
    )
