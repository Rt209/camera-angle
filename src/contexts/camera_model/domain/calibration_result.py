from __future__ import annotations

from dataclasses import dataclass, field

from src.contexts.camera_model.domain.intrinsics import CameraIntrinsics


@dataclass(frozen=True)
class CalibrationResult:
    intrinsics: CameraIntrinsics
    reprojection_error: float
    calibration_pattern: str
    calibration_frame_count: int
    attempted_frame_count: int
    source: str
    board_rows: int
    board_cols: int
    square_size: float
    debug_images: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = self.intrinsics.to_dict()
        data.update(
            {
                "reprojection_error": self.reprojection_error,
                "calibration_pattern": self.calibration_pattern,
                "calibration_frame_count": self.calibration_frame_count,
                "attempted_frame_count": self.attempted_frame_count,
                "source": self.source,
                "board_rows": self.board_rows,
                "board_cols": self.board_cols,
                "square_size": self.square_size,
                "debug_images": self.debug_images,
                "warnings": self.warnings,
            }
        )
        return data

