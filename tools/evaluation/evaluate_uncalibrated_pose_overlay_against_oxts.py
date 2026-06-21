from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.dataset.kitti_pose_video import PoseAngles, load_poses


COMPARISON_COLUMNS = [
    "frame_index",
    "timestamp_sec",
    "pred_relative_yaw",
    "oxts_absolute_yaw",
    "oxts_relative_yaw",
    "yaw_error",
    "abs_yaw_error",
    "pred_relative_pitch",
    "oxts_absolute_pitch",
    "oxts_relative_pitch",
    "pitch_error",
    "abs_pitch_error",
    "pred_relative_roll",
    "oxts_absolute_roll",
    "oxts_relative_roll",
    "roll_error",
    "abs_roll_error",
    "tracked_point_count",
    "inlier_count",
    "inlier_ratio",
    "confidence",
    "warnings",
]


@dataclass(frozen=True)
class OpticalFlowPoseEvaluationOutputs:
    comparison_csv: Path
    summary_json: Path
    worst_frames_csv: Path
    report_md: Path
    plot_paths: dict[str, Path]


def run_evaluation(pose_json: Path, oxts_dir: Path, output_dir: Path) -> OpticalFlowPoseEvaluationOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    pose_rows = _read_pose_json(pose_json)
    oxts_poses = load_poses(oxts_dir)
    comparison = evaluate_rows(pose_rows, oxts_poses)

    comparison_csv = output_dir / "relative_pose_vs_oxts.csv"
    summary_json = output_dir / "relative_pose_vs_oxts_summary.json"
    worst_frames_csv = output_dir / "worst_frames.csv"
    report_md = output_dir / "evaluation_report.md"

    _write_csv(comparison_csv, comparison, COMPARISON_COLUMNS)
    summary = build_summary(comparison)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_csv(worst_frames_csv, build_worst_frames(comparison), ["rank", "metric", *COMPARISON_COLUMNS])
    plot_paths = write_plots(comparison, output_dir)
    report_md.write_text(render_report(summary, comparison, plot_paths), encoding="utf-8")
    return OpticalFlowPoseEvaluationOutputs(comparison_csv, summary_json, worst_frames_csv, report_md, plot_paths)


def evaluate_rows(pose_rows: list[dict[str, Any]], oxts_poses: list[PoseAngles]) -> list[dict[str, Any]]:
    comparison = []
    for row in pose_rows:
        frame_index = int(row["frame_index"])
        if frame_index <= 0 or frame_index >= len(oxts_poses):
            continue
        oxts_abs = oxts_poses[frame_index]
        oxts_prev = oxts_poses[frame_index - 1]
        rel = PoseAngles(
            yaw_deg=_angle_delta(oxts_abs.yaw_deg, oxts_prev.yaw_deg),
            pitch_deg=_angle_delta(oxts_abs.pitch_deg, oxts_prev.pitch_deg),
            roll_deg=_angle_delta(oxts_abs.roll_deg, oxts_prev.roll_deg),
        )
        pred_yaw = _parse_float(row.get("yaw_deg"))
        pred_pitch = _parse_float(row.get("pitch_deg"))
        pred_roll = _parse_float(row.get("roll_deg"))
        yaw_error = _error(pred_yaw, rel.yaw_deg)
        pitch_error = _error(pred_pitch, rel.pitch_deg)
        roll_error = _error(pred_roll, rel.roll_deg)
        comparison.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": _parse_float(row.get("timestamp_sec")),
                "pred_relative_yaw": pred_yaw,
                "oxts_absolute_yaw": oxts_abs.yaw_deg,
                "oxts_relative_yaw": rel.yaw_deg,
                "yaw_error": yaw_error,
                "abs_yaw_error": abs(yaw_error) if yaw_error is not None else None,
                "pred_relative_pitch": pred_pitch,
                "oxts_absolute_pitch": oxts_abs.pitch_deg,
                "oxts_relative_pitch": rel.pitch_deg,
                "pitch_error": pitch_error,
                "abs_pitch_error": abs(pitch_error) if pitch_error is not None else None,
                "pred_relative_roll": pred_roll,
                "oxts_absolute_roll": oxts_abs.roll_deg,
                "oxts_relative_roll": rel.roll_deg,
                "roll_error": roll_error,
                "abs_roll_error": abs(roll_error) if roll_error is not None else None,
                "tracked_point_count": int(row.get("tracked_point_count") or 0),
                "inlier_count": int(row.get("inlier_count") or 0),
                "inlier_ratio": _parse_float(row.get("inlier_ratio")),
                "confidence": _parse_float(row.get("confidence")),
                "warnings": "|".join(row.get("warnings") or []),
            }
        )
    return comparison


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "comparison_type": "predicted_frame_to_frame_relative_rotation_vs_oxts_frame_to_frame_delta",
        "calibrated_pose_result": False,
        "prototype_warnings": ["intrinsics_not_calibrated", "approximate_K_used", "pose_for_debug_only"],
        "total_rows": len(rows),
        "mean_inlier_ratio": _mean(rows, "inlier_ratio"),
        "mean_confidence": _mean(rows, "confidence"),
        "mean_abs_yaw_error": _mean_abs(rows, "yaw"),
        "median_abs_yaw_error": _median_abs(rows, "yaw"),
        "max_abs_yaw_error": _max_abs(rows, "yaw"),
        "rmse_yaw_error": _rmse(rows, "yaw"),
        "mean_abs_pitch_error": _mean_abs(rows, "pitch"),
        "median_abs_pitch_error": _median_abs(rows, "pitch"),
        "max_abs_pitch_error": _max_abs(rows, "pitch"),
        "rmse_pitch_error": _rmse(rows, "pitch"),
        "mean_abs_roll_error": _mean_abs(rows, "roll"),
        "median_abs_roll_error": _median_abs(rows, "roll"),
        "max_abs_roll_error": _max_abs(rows, "roll"),
        "rmse_roll_error": _rmse(rows, "roll"),
        "top_10_yaw_error_frames": _top_error_frames(rows, "yaw", 10),
        "top_10_pitch_error_frames": _top_error_frames(rows, "pitch", 10),
        "top_10_roll_error_frames": _top_error_frames(rows, "roll", 10),
    }


def build_worst_frames(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    worst = []
    for metric in ("yaw", "pitch", "roll"):
        for rank, row in enumerate(_top_error_frames(rows, metric, limit), start=1):
            full = next(source for source in rows if source["frame_index"] == row["frame_index"])
            worst.append({"rank": rank, "metric": metric, **full})
    return worst


def write_plots(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    paths = {
        "yaw": output_dir / "yaw_relative_pred_vs_oxts_delta.png",
        "pitch": output_dir / "pitch_relative_pred_vs_oxts_delta.png",
        "roll": output_dir / "roll_relative_pred_vs_oxts_delta.png",
        "abs_error": output_dir / "abs_error_by_frame.png",
        "confidence": output_dir / "confidence_vs_abs_error.png",
    }
    for angle in ("yaw", "pitch", "roll"):
        _plot_relative(rows, angle, paths[angle])
    _plot_abs_error(rows, paths["abs_error"])
    _plot_confidence(rows, paths["confidence"])
    return paths


def render_report(summary: dict[str, Any], rows: list[dict[str, Any]], plot_paths: dict[str, Path]) -> str:
    lines = [
        "# Optical Flow Uncalibrated Pose vs KITTI OXTS Evaluation",
        "",
        "This report compares the optical-flow prototype's frame-to-frame relative yaw/pitch/roll against KITTI OXTS frame-to-frame angle deltas.",
        "",
        "Important caveat: this is not a calibrated pose result. The overlay uses approximate K and every pose row is marked with `intrinsics_not_calibrated`, `approximate_K_used`, and `pose_for_debug_only`.",
        "",
        "## Summary",
        "",
        f"- Rows compared: {summary['total_rows']}",
        f"- Mean inlier ratio: {_fmt(summary['mean_inlier_ratio'])}",
        f"- Mean confidence: {_fmt(summary['mean_confidence'])}",
        f"- Mean abs yaw error: {_fmt(summary['mean_abs_yaw_error'])} deg",
        f"- Mean abs pitch error: {_fmt(summary['mean_abs_pitch_error'])} deg",
        f"- Mean abs roll error: {_fmt(summary['mean_abs_roll_error'])} deg",
        f"- RMSE yaw/pitch/roll: {_fmt(summary['rmse_yaw_error'])}, {_fmt(summary['rmse_pitch_error'])}, {_fmt(summary['rmse_roll_error'])} deg",
        "",
        "## Plots",
        "",
        f"![Yaw relative predicted vs OXTS delta]({plot_paths['yaw'].name})",
        "",
        f"![Pitch relative predicted vs OXTS delta]({plot_paths['pitch'].name})",
        "",
        f"![Roll relative predicted vs OXTS delta]({plot_paths['roll'].name})",
        "",
        f"![Absolute error by frame]({plot_paths['abs_error'].name})",
        "",
        f"![Confidence vs absolute error]({plot_paths['confidence'].name})",
        "",
        "## Analysis",
        "",
        "- The optical-flow prototype produces relative rotations from image correspondences, so the fair comparison is against OXTS frame-to-frame deltas rather than OXTS absolute global yaw/pitch/roll.",
        "- Confidence is intentionally damped by `intrinsics_quality = 0.4` because K is approximate. Treat high inlier ratios as tracking/geometric consistency, not calibration quality.",
        "- Large yaw errors usually indicate that approximate intrinsics, forward-motion degeneracy, or scene-depth variation is dominating the Essential Matrix solution.",
        "- Pitch and roll errors should be interpreted as relative-frame debug signals until a real calibration video provides camera intrinsics.",
        "",
        "## Worst Frames",
        "",
    ]
    for metric in ("yaw", "pitch", "roll"):
        lines.append(f"### {metric.title()}")
        for item in summary[f"top_10_{metric}_error_frames"][:5]:
            lines.append(
                f"- frame {item['frame_index']}: pred={_fmt(item['predicted'])}, "
                f"oxts_delta={_fmt(item['oxts_delta'])}, abs_error={_fmt(item['abs_error'])}, "
                f"confidence={_fmt(item['confidence'])}"
            )
        lines.append("")
    return "\n".join(lines)


def _read_pose_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["frames"])


def _plot_relative(rows: list[dict[str, Any]], angle: str, output_path: Path) -> None:
    frames = [row["frame_index"] for row in rows]
    plt.figure(figsize=(11, 5))
    plt.plot(frames, [row[f"pred_relative_{angle}"] for row in rows], label=f"pred relative {angle}", linewidth=1.4)
    plt.plot(frames, [row[f"oxts_relative_{angle}"] for row in rows], label=f"OXTS delta {angle}", linewidth=1.4)
    plt.title(f"{angle.upper()} relative prediction vs OXTS delta")
    plt.xlabel("frame_index")
    plt.ylabel(f"{angle} degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _plot_abs_error(rows: list[dict[str, Any]], output_path: Path) -> None:
    frames = [row["frame_index"] for row in rows]
    plt.figure(figsize=(11, 5))
    for angle in ("yaw", "pitch", "roll"):
        plt.plot(frames, [row[f"abs_{angle}_error"] for row in rows], label=f"abs {angle} error", linewidth=1.3)
    plt.title("Optical-flow relative pose absolute error by frame")
    plt.xlabel("frame_index")
    plt.ylabel("absolute error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _plot_confidence(rows: list[dict[str, Any]], output_path: Path) -> None:
    plt.figure(figsize=(8, 6))
    for angle in ("yaw", "pitch", "roll"):
        xs = [row["confidence"] for row in rows]
        ys = [row[f"abs_{angle}_error"] for row in rows]
        plt.scatter(xs, ys, s=18, alpha=0.65, label=f"{angle} abs error")
    plt.title("Optical-flow confidence vs absolute error")
    plt.xlabel("confidence")
    plt.ylabel("absolute error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _top_error_frames(rows: list[dict[str, Any]], angle: str, limit: int) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: row[f"abs_{angle}_error"] or -1, reverse=True)
    return [
        {
            "frame_index": row["frame_index"],
            "timestamp_sec": row["timestamp_sec"],
            "predicted": row[f"pred_relative_{angle}"],
            "oxts_delta": row[f"oxts_relative_{angle}"],
            "error": row[f"{angle}_error"],
            "abs_error": row[f"abs_{angle}_error"],
            "confidence": row["confidence"],
            "inlier_ratio": row["inlier_ratio"],
        }
        for row in sorted_rows[:limit]
    ]


def _angle_delta(current: float, previous: float) -> float:
    return ((current - previous + 180.0) % 360.0) - 180.0


def _error(predicted: float | None, expected: float) -> float | None:
    if predicted is None:
        return None
    return _angle_delta(predicted, expected)


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = _values(rows, key)
    return mean(values) if values else None


def _mean_abs(rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _values(rows, f"abs_{angle}_error")
    return mean(values) if values else None


def _median_abs(rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _values(rows, f"abs_{angle}_error")
    return median(values) if values else None


def _max_abs(rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _values(rows, f"abs_{angle}_error")
    return max(values) if values else None


def _rmse(rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _values(rows, f"{angle}_error")
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate uncalibrated optical-flow pose overlay against KITTI OXTS deltas.")
    parser.add_argument(
        "--pose-json",
        type=Path,
        default=Path("outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json"),
    )
    parser.add_argument("--oxts-dir", type=Path, default=Path("tools/input/oxts"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    outputs = run_evaluation(args.pose_json, args.oxts_dir, args.output_dir)
    print(f"Wrote comparison CSV: {outputs.comparison_csv}")
    print(f"Wrote summary JSON: {outputs.summary_json}")
    print(f"Wrote worst frames CSV: {outputs.worst_frames_csv}")
    print(f"Wrote report: {outputs.report_md}")
    for path in outputs.plot_paths.values():
        print(f"Wrote plot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
