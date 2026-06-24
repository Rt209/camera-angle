from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.evaluation.geometry_service import (  # noqa: E402
    GeometryEvaluationConfig,
    evaluate_geometry_pose,
    evaluate_standalone_geometry_pose,
)
from src.shared.repository_paths import RepositoryPaths  # noqa: E402

REPOSITORY_PATHS = RepositoryPaths(PROJECT_ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate video pose timeline against KITTI OXTS poses."
    )
    parser.add_argument(
        "--pose-csv", type=Path,
        default=REPOSITORY_PATHS.outputs_root / "video_pose/pose_timeline.csv",
    )
    parser.add_argument(
        "--oxts-dir",
        type=Path,
        default=REPOSITORY_PATHS.sample_oxts,
    )
    parser.add_argument(
        "--output-dir", type=Path,
        help="Evaluation output directory. Defaults to outputs/<run_id>/eval/geometry.",
    )
    parser.add_argument(
        "--theta-deg", type=float, default=3.0,
        help="Acceptable geodesic pose error in degrees.",
    )
    parser.add_argument("--save-plots", action="store_true", help="Write diagnostic PNG plots.")
    parser.add_argument("--save-worst-frames", action="store_true", help="Write worst_frames.csv.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = GeometryEvaluationConfig(
            theta_deg=args.theta_deg,
            save_plots=args.save_plots,
            save_worst_frames=args.save_worst_frames,
        )
        if args.output_dir is None:
            outputs = evaluate_standalone_geometry_pose(
                args.pose_csv, args.oxts_dir, REPOSITORY_PATHS, config
            )
        else:
            outputs = evaluate_geometry_pose(
                args.pose_csv, args.oxts_dir, args.output_dir, config
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 1
    _print_outputs(outputs)
    return 0


def _print_outputs(outputs: object) -> None:
    print(f"Wrote comparison CSV: {outputs.comparison_csv}")
    print(f"Wrote summary JSON: {outputs.summary_json}")
    print(f"Wrote report: {outputs.report_md}")
    if outputs.worst_frames_csv is not None:
        print(f"Wrote worst frames CSV: {outputs.worst_frames_csv}")
    for path in outputs.plot_paths.values():
        print(f"Wrote plot: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
