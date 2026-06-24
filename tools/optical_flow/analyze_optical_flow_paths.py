from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.contexts.motion_analysis.services.sparse_flow_tracker import (
    LucasKanadeConfig,
    ShiTomasiConfig,
    SparseFlowTracker,
    SparseFlowTrackerConfig,
)
from src.contexts.output.services.motion_debug_visualizer import write_sparse_flow_debug_frames


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze sparse optical flow tracks with Shi-Tomasi + LK.")
    parser.add_argument("--video", type=Path, default=Path("data/samples/kitti/videos/kitti_no_overlay.mp4"))
    parser.add_argument("--debug-dir", type=Path, default=Path("outputs/optical_flow_pose/sparse_flow"))
    parser.add_argument("--frame-step", type=int, default=1)
    parser.add_argument("--max-debug-frames", type=int, default=120)
    parser.add_argument("--output-debug-every-n-frames", type=int, default=10)
    parser.add_argument("--max-corners", type=int, default=1000)
    parser.add_argument("--quality-level", type=float, default=0.01)
    parser.add_argument("--min-distance", type=int, default=8)
    parser.add_argument("--lk-win-size", type=int, default=21)
    parser.add_argument("--lk-max-level", type=int, default=3)
    parser.add_argument("--lk-criteria-count", type=int, default=30)
    parser.add_argument("--lk-criteria-eps", type=float, default=0.01)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SparseFlowTrackerConfig(
        feature=ShiTomasiConfig(
            max_corners=args.max_corners,
            quality_level=args.quality_level,
            min_distance=args.min_distance,
        ),
        lk=LucasKanadeConfig(
            win_size=(args.lk_win_size, args.lk_win_size),
            max_level=args.lk_max_level,
            criteria_count=args.lk_criteria_count,
            criteria_eps=args.lk_criteria_eps,
        ),
        frame_step=args.frame_step,
        write_debug_frames=True,
        max_debug_frames=args.max_debug_frames,
        output_debug_every_n_frames=args.output_debug_every_n_frames,
    )
    result = SparseFlowTracker(config).track_video(args.video)
    args.debug_dir.mkdir(parents=True, exist_ok=True)
    debug_frame_dir = args.debug_dir / "debug_frames"
    debug_paths = write_sparse_flow_debug_frames(debug_frame_dir, result.debug_frames)

    summary = result.to_summary_dict()
    summary["debug_outputs"] = debug_paths
    summary_path = args.debug_dir / "flow_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    tracks_path = args.debug_dir / "flow_tracks.csv"
    _write_tracks_csv(tracks_path, result)

    aggregate = result.aggregate_summary()
    print(f"Wrote summary: {summary_path}")
    print(f"Wrote tracks: {tracks_path}")
    print(f"Wrote debug frames: {debug_frame_dir}")
    print(f"Processed frames: {aggregate['processed_frame_count']}")
    print(f"Total flow vectors: {aggregate['total_flow_vector_count']}")
    print(f"Mean valid tracks: {aggregate['mean_valid_track_count']:.2f}")
    print(f"Mean flow magnitude: {aggregate['mean_flow_magnitude']:.3f} px/frame")
    return 0


def _write_tracks_csv(path: Path, result: object) -> None:
    fieldnames = [
        "track_id",
        "frame_index",
        "timestamp_sec",
        "x0",
        "y0",
        "x1",
        "y1",
        "dx",
        "dy",
        "magnitude",
        "direction_deg",
        "lk_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for vector in result.flow_vectors:
            writer.writerow(vector.to_csv_row())


if __name__ == "__main__":
    raise SystemExit(main())
