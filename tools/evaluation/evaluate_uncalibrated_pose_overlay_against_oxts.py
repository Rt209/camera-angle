from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.evaluation.optical_flow_service import (  # noqa: E402
    OpticalFlowEvaluationConfig,
    evaluate_optical_flow_pose,
    evaluate_standalone_optical_flow_pose,
)
from src.contexts.camera_model.domain.extrinsics import load_camera_extrinsics  # noqa: E402
from src.contexts.camera_model.services.kitti_calibration_loader import load_kitti_calibration  # noqa: E402
from src.shared.repository_paths import RepositoryPaths  # noqa: E402

REPOSITORY_PATHS = RepositoryPaths(PROJECT_ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate optical-flow relative pose against KITTI OXTS camera-motion deltas."
    )
    parser.add_argument(
        "--pose-json", type=Path,
        default=REPOSITORY_PATHS.outputs_root / "optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json",
    )
    parser.add_argument(
        "--oxts-dir", type=Path,
        default=REPOSITORY_PATHS.sample_oxts,
    )
    parser.add_argument(
        "--output-dir", type=Path,
        help="Evaluation output directory. Defaults to outputs/<run_id>/eval/optical.",
    )
    parser.add_argument(
        "--theta-deg", type=float, default=1.0,
        help="Acceptable geodesic pose error in degrees.",
    )
    parser.add_argument("--save-plots", action="store_true", help="Write diagnostic PNG plots.")
    parser.add_argument("--save-worst-frames", action="store_true", help="Write worst_frames.csv.")
    parser.add_argument(
        "--camera-extrinsics",
        type=Path,
        help="Optional camera-to-vehicle extrinsics JSON.",
    )
    parser.add_argument(
        "--kitti-calibration-dir",
        type=Path,
        help="KITTI date calibration directory containing the three calibration txt files.",
    )
    parser.add_argument(
        "--kitti-camera-index", choices=("00", "01", "02", "03"), default="03"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.camera_extrinsics is not None and args.kitti_calibration_dir is not None:
            raise ValueError(
                "Use either --camera-extrinsics or --kitti-calibration-dir, not both."
            )
        if args.kitti_calibration_dir is not None:
            profile = load_kitti_calibration(
                args.kitti_calibration_dir, args.kitti_camera_index
            )
            camera_to_vehicle_rotation = profile.extrinsics.camera_to_vehicle_rotation
            extrinsics_source = profile.extrinsics.source
        elif args.camera_extrinsics is not None:
            extrinsics = load_camera_extrinsics(args.camera_extrinsics)
            camera_to_vehicle_rotation = extrinsics.camera_to_vehicle_rotation
            extrinsics_source = extrinsics.source
        else:
            camera_to_vehicle_rotation = None
            extrinsics_source = None
        config = OpticalFlowEvaluationConfig(
            theta_deg=args.theta_deg,
            save_plots=args.save_plots,
            save_worst_frames=args.save_worst_frames,
            camera_to_vehicle_rotation=camera_to_vehicle_rotation,
            extrinsics_source=extrinsics_source,
        )
        if args.output_dir is None:
            outputs = evaluate_standalone_optical_flow_pose(
                args.pose_json, args.oxts_dir, REPOSITORY_PATHS, config
            )
        else:
            outputs = evaluate_optical_flow_pose(
                args.pose_json, args.oxts_dir, args.output_dir, config
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote comparison CSV: {outputs.comparison_csv}")
    print(f"Wrote summary JSON: {outputs.summary_json}")
    print(f"Wrote report: {outputs.report_md}")
    if outputs.worst_frames_csv is not None:
        print(f"Wrote worst frames CSV: {outputs.worst_frames_csv}")
    for path in outputs.plot_paths.values():
        print(f"Wrote plot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
