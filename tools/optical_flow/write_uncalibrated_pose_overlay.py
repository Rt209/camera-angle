from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.optical_flow_pose_overlay_pipeline import UncalibratedPoseOverlayConfig, UncalibratedPoseOverlayPipeline
from src.contexts.motion_analysis.services.sparse_flow_tracker import SparseFlowTrackerConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write uncalibrated debug pose overlay from sparse optical flow.")
    parser.add_argument("--video", type=Path, default=Path("tools/output/kitti_no_overlay.mp4"))
    parser.add_argument("--debug-dir", type=Path, default=Path("outputs/optical_flow_pose/pose_overlay_uncalibrated"))
    parser.add_argument("--max-debug-frames", type=int, default=120)
    parser.add_argument("--output-debug-every-n-frames", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = UncalibratedPoseOverlayConfig(
        sparse_flow=SparseFlowTrackerConfig(
            max_debug_frames=args.max_debug_frames,
            output_debug_every_n_frames=args.output_debug_every_n_frames,
        ),
        output_debug_every_n_frames=args.output_debug_every_n_frames,
    )
    result = UncalibratedPoseOverlayPipeline(config).run(args.video, args.debug_dir)
    summary = result.summary()
    print(f"Wrote overlay video: {result.output_video}")
    print(f"Wrote timeline CSV: {result.pose_timeline_csv}")
    print(f"Wrote frame JSON: {result.frame_pose_results_json}")
    print(f"Pose frames: {summary['pose_frame_count']}")
    print(f"Mean inlier ratio: {summary['mean_inlier_ratio']:.3f}")
    print(f"Mean confidence: {summary['mean_confidence']:.3f}")
    print("Warnings: intrinsics_not_calibrated, approximate_K_used, pose_for_debug_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
