from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contexts.camera_model.services.calibration_board_detector import CalibrationBoardConfig
from src.contexts.camera_model.services.calibration_frame_sampler import CalibrationFrameSamplerConfig
from src.contexts.camera_model.services.camera_calibrator import CameraCalibrationConfig, CameraCalibrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calibrate camera intrinsics from a chessboard/Charuco video.")
    parser.add_argument("--calibration-video", required=True, type=Path)
    parser.add_argument("--pattern", choices=["chessboard", "charuco"], default="chessboard")
    parser.add_argument("--board-rows", type=int, default=6, help="Number of inner-corner rows.")
    parser.add_argument("--board-cols", type=int, default=9, help="Number of inner-corner columns.")
    parser.add_argument("--square-size", type=float, default=1.0)
    parser.add_argument("--frame-step", type=int, default=5)
    parser.add_argument("--max-frames", type=int, default=80)
    parser.add_argument("--min-valid-frames", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/optical_flow_pose/calibration/camera_intrinsics.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("outputs/optical_flow_pose/calibration/calibration_report.md"),
    )
    parser.add_argument(
        "--detected-corners-dir",
        type=Path,
        default=Path("outputs/optical_flow_pose/calibration/detected_corners"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = CameraCalibrationConfig(
        board=CalibrationBoardConfig(
            pattern=args.pattern,
            board_rows=args.board_rows,
            board_cols=args.board_cols,
            square_size=args.square_size,
        ),
        sampler=CalibrationFrameSamplerConfig(frame_step=args.frame_step, max_frames=args.max_frames),
        min_valid_frames=args.min_valid_frames,
        source_label="calibration_video",
    )
    calibrator = CameraCalibrator(config)
    result = calibrator.calibrate_from_video(args.calibration_video, args.detected_corners_dir)
    calibrator.write_outputs(result, args.output, args.report)
    print(f"Wrote intrinsics: {args.output}")
    print(f"Wrote report: {args.report}")
    print(f"Valid frames: {result.calibration_frame_count}/{result.attempted_frame_count}")
    print(f"Reprojection error: {result.reprojection_error:.6f} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
