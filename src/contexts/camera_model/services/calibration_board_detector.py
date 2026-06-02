from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class CalibrationBoardConfig:
    pattern: str = "chessboard"
    board_rows: int = 6
    board_cols: int = 9
    square_size: float = 1.0

    def validate(self) -> None:
        if self.pattern not in {"chessboard", "charuco"}:
            raise ValueError("pattern must be 'chessboard' or 'charuco'.")
        if self.board_rows < 2 or self.board_cols < 2:
            raise ValueError("board_rows and board_cols must be at least 2.")
        if self.square_size <= 0:
            raise ValueError("square_size must be greater than zero.")


@dataclass(frozen=True)
class BoardDetection:
    found: bool
    object_points: np.ndarray | None
    image_points: np.ndarray | None
    corners: np.ndarray | None
    annotated_bgr: np.ndarray | None
    message: str = ""


class CalibrationBoardDetector:
    def __init__(self, config: CalibrationBoardConfig) -> None:
        config.validate()
        self.config = config

    def detect(self, image_bgr: np.ndarray) -> BoardDetection:
        if self.config.pattern == "charuco":
            return self._detect_charuco(image_bgr)
        return self._detect_chessboard(image_bgr)

    def object_points_template(self) -> np.ndarray:
        points = np.zeros((self.config.board_rows * self.config.board_cols, 3), np.float32)
        grid_x, grid_y = np.meshgrid(np.arange(self.config.board_cols), np.arange(self.config.board_rows))
        points[:, :2] = np.column_stack((grid_x.reshape(-1), grid_y.reshape(-1)))
        return points * float(self.config.square_size)

    def _detect_chessboard(self, image_bgr: np.ndarray) -> BoardDetection:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        pattern_size = (self.config.board_cols, self.config.board_rows)
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
        found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
        if not found or corners is None:
            return BoardDetection(False, None, None, None, None, "chessboard corners not found")

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        annotated = image_bgr.copy()
        cv2.drawChessboardCorners(annotated, pattern_size, refined, found)
        return BoardDetection(
            found=True,
            object_points=self.object_points_template(),
            image_points=refined.reshape(-1, 2).astype(np.float32),
            corners=refined,
            annotated_bgr=annotated,
        )

    def _detect_charuco(self, image_bgr: np.ndarray) -> BoardDetection:
        aruco = getattr(cv2, "aruco", None)
        if aruco is None:
            raise RuntimeError("Charuco calibration requires opencv-contrib-python with cv2.aruco.")
        if not hasattr(aruco, "calibrateCameraCharuco"):
            raise RuntimeError(
                "Charuco calibration requires an OpenCV build with cv2.aruco.calibrateCameraCharuco; "
                "use --pattern chessboard with this environment."
            )
        raise RuntimeError("Charuco calibration support is not wired yet; use --pattern chessboard.")
