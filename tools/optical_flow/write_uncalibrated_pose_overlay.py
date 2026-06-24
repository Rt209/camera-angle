from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.optical_flow_pose_overlay_pipeline import UncalibratedPoseOverlayConfig, UncalibratedPoseOverlayPipeline
from src.contexts.motion_analysis.services.sparse_flow_tracker import SparseFlowTrackerConfig
from src.shared.repository_paths import RepositoryPaths
from src.shared.run_directory import RunDirectoryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write calibrated or approximate-intrinsics relative pose overlay from sparse optical flow.")
    parser.add_argument("--video", type=Path, default=Path("data/samples/kitti/videos/kitti_no_overlay.mp4"))
    parser.add_argument("--debug-dir", type=Path, help="Optical artifact directory. Defaults to outputs/<run_id>/optical.")
    parser.add_argument("--max-debug-frames", type=int, default=120)
    parser.add_argument("--max-processing-frames", type=int)
    parser.add_argument("--write-debug-frames", action="store_true")
    parser.add_argument("--camera-intrinsics", type=Path, help="Optional camera_intrinsics.json from calibration.")
    parser.add_argument(
        "--kitti-calibration-dir",
        type=Path,
        help="KITTI date calibration directory containing calib_cam_to_cam.txt.",
    )
    parser.add_argument(
        "--kitti-camera-index", choices=("00", "01", "02", "03"), default="03"
    )
    parser.add_argument(
        "--debug-every-n-frames", "--output-debug-every-n-frames",
        dest="debug_every_n_frames", type=int, default=10,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = args.debug_dir or (
        RunDirectoryService(RepositoryPaths.discover().outputs_root).next_run_path() / "optical"
    )
    config = UncalibratedPoseOverlayConfig(
        sparse_flow=SparseFlowTrackerConfig(
            max_processing_frames=args.max_processing_frames,
            write_debug_frames=False,
            max_debug_frames=args.max_debug_frames,
        ),
        write_debug_frames=args.write_debug_frames,
        debug_every_n_frames=args.debug_every_n_frames,
        max_debug_frames=args.max_debug_frames,
        camera_intrinsics_path=args.camera_intrinsics,
        kitti_calibration_directory=args.kitti_calibration_dir,
        kitti_camera_index=args.kitti_camera_index,
    )
    result = UncalibratedPoseOverlayPipeline(config).run(args.video, output_dir)
    summary = result.summary()
    print(f"Wrote overlay video: {result.output_video}")
    print(f"Wrote timeline CSV: {result.pose_timeline_csv}")
    print(f"Wrote frame JSON: {result.frame_pose_results_json}")
    print(f"Pose frames: {summary['pose_frame_count']}")
    print(f"Mean inlier ratio: {summary['mean_inlier_ratio']:.3f}")
    print(f"Mean confidence: {summary['mean_confidence']:.3f}")
    print(f"Intrinsics source: {summary['intrinsics_source']}")
    if summary["warnings"]:
        print(f"Warnings: {', '.join(summary['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
