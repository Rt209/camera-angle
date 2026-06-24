from dataclasses import dataclass

from .pose_record import PredictionRecord, ReferencePose


@dataclass(frozen=True)
class AlignedPosePair:
    prediction: PredictionRecord
    reference: ReferencePose
    previous_reference: ReferencePose | None
    comparison_type: str
