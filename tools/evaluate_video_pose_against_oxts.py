from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.kitti_pose_video import PoseAngles, load_poses


EVALUATION_COLUMNS = [
    "frame_index",
    "time_sec",
    "pred_yaw",
    "oxts_yaw",
    "yaw_error",
    "abs_yaw_error",
    "pred_pitch",
    "oxts_pitch",
    "pitch_error",
    "abs_pitch_error",
    "pred_roll",
    "oxts_roll",
    "roll_error",
    "abs_roll_error",
    "confidence",
    "yaw_confidence",
    "pitch_confidence",
    "roll_confidence",
    "status",
    "detected_line_count",
    "near_horizontal_count",
    "near_vertical_count",
    "perspective_line_count",
    "vanishing_point_candidate_count",
    "horizon_candidate_count",
]

WORST_COLUMNS = [
    "rank",
    "metric",
    "frame_index",
    "time_sec",
    "pred_value",
    "oxts_value",
    "error",
    "abs_error",
    "confidence",
    "status",
    "detected_line_count",
    "perspective_line_count",
    "vanishing_point_candidate_count",
    "horizon_candidate_count",
]


@dataclass(frozen=True)
class EvaluationOutputs:
    comparison_csv: Path
    summary_json: Path
    worst_frames_csv: Path
    plot_paths: dict[str, Path]


def read_pose_timeline(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as file:
        return [_parse_pose_row(row) for row in csv.DictReader(file)]


def evaluate_rows(pose_rows: list[dict[str, Any]], oxts_poses: list[PoseAngles]) -> list[dict[str, Any]]:
    evaluated: list[dict[str, Any]] = []
    for row in pose_rows:
        frame_index = row["frame_index"]
        if frame_index >= len(oxts_poses):
            raise ValueError(
                f"OXTS pose count ({len(oxts_poses)}) is smaller than required frame_index {frame_index}."
            )

        pose = oxts_poses[frame_index]
        evaluated.append(_evaluate_row(row, pose))
    return evaluated


def write_evaluation_outputs(
    evaluated_rows: list[dict[str, Any]],
    output_dir: Path,
) -> EvaluationOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_csv = output_dir / "pose_vs_oxts.csv"
    summary_json = output_dir / "pose_vs_oxts_summary.json"
    worst_frames_csv = output_dir / "worst_frames.csv"

    _write_csv(comparison_csv, evaluated_rows, EVALUATION_COLUMNS)
    summary = build_summary(evaluated_rows)
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    _write_csv(worst_frames_csv, build_worst_frames(evaluated_rows, limit=10), WORST_COLUMNS)

    plot_paths = write_plots(evaluated_rows, output_dir)
    return EvaluationOutputs(
        comparison_csv=comparison_csv,
        summary_json=summary_json,
        worst_frames_csv=worst_frames_csv,
        plot_paths=plot_paths,
    )


def build_summary(evaluated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_rows": len(evaluated_rows),
        "valid_yaw_count": len(_valid_abs_errors(evaluated_rows, "yaw")),
        "valid_pitch_count": len(_valid_abs_errors(evaluated_rows, "pitch")),
        "valid_roll_count": len(_valid_abs_errors(evaluated_rows, "roll")),
        "mean_abs_yaw_error": _mean_abs(evaluated_rows, "yaw"),
        "median_abs_yaw_error": _median_abs(evaluated_rows, "yaw"),
        "max_abs_yaw_error": _max_abs(evaluated_rows, "yaw"),
        "rmse_yaw_error": _rmse(evaluated_rows, "yaw"),
        "mean_abs_pitch_error": _mean_abs(evaluated_rows, "pitch"),
        "median_abs_pitch_error": _median_abs(evaluated_rows, "pitch"),
        "max_abs_pitch_error": _max_abs(evaluated_rows, "pitch"),
        "rmse_pitch_error": _rmse(evaluated_rows, "pitch"),
        "mean_abs_roll_error": _mean_abs(evaluated_rows, "roll"),
        "median_abs_roll_error": _median_abs(evaluated_rows, "roll"),
        "max_abs_roll_error": _max_abs(evaluated_rows, "roll"),
        "rmse_roll_error": _rmse(evaluated_rows, "roll"),
        "top_10_yaw_error_frames": _top_error_frames(evaluated_rows, "yaw", 10),
        "top_10_pitch_error_frames": _top_error_frames(evaluated_rows, "pitch", 10),
        "top_10_roll_error_frames": _top_error_frames(evaluated_rows, "roll", 10),
    }


def build_worst_frames(evaluated_rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    worst: list[dict[str, Any]] = []
    for metric in ("yaw", "pitch", "roll"):
        for rank, row in enumerate(_top_error_frames(evaluated_rows, metric, limit), start=1):
            worst.append(
                {
                    "rank": rank,
                    "metric": metric,
                    "frame_index": row["frame_index"],
                    "time_sec": row["time_sec"],
                    "pred_value": row["predicted_value"],
                    "oxts_value": row["oxts_value"],
                    "error": row["error"],
                    "abs_error": row["abs_error"],
                    "confidence": row["confidence"],
                    "status": row["status"],
                    "detected_line_count": row["detected_line_count"],
                    "perspective_line_count": row["perspective_line_count"],
                    "vanishing_point_candidate_count": row["vanishing_point_candidate_count"],
                    "horizon_candidate_count": row["horizon_candidate_count"],
                }
            )
    return worst


def write_plots(evaluated_rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    plot_paths = {
        "yaw": output_dir / "yaw_pred_vs_oxts.png",
        "pitch": output_dir / "pitch_pred_vs_oxts.png",
        "roll": output_dir / "roll_pred_vs_oxts.png",
        "abs_error": output_dir / "abs_error_by_frame.png",
        "confidence": output_dir / "confidence_vs_abs_error.png",
    }
    _plot_pred_vs_oxts(evaluated_rows, "yaw", plot_paths["yaw"])
    _plot_pred_vs_oxts(evaluated_rows, "pitch", plot_paths["pitch"])
    _plot_pred_vs_oxts(evaluated_rows, "roll", plot_paths["roll"])
    _plot_abs_error(evaluated_rows, plot_paths["abs_error"])
    _plot_confidence_vs_abs_error(evaluated_rows, plot_paths["confidence"])
    return plot_paths


def run_evaluation(pose_csv: Path, oxts_dir: Path, output_dir: Path) -> EvaluationOutputs:
    pose_rows = read_pose_timeline(pose_csv)
    oxts_poses = load_poses(oxts_dir)
    evaluated_rows = evaluate_rows(pose_rows, oxts_poses)
    return write_evaluation_outputs(evaluated_rows, output_dir)


def _parse_pose_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "frame_index": int(row["frame_index"]),
        "time_sec": _parse_float(row.get("time_sec")),
        "yaw": _parse_float(row.get("yaw")),
        "pitch": _parse_float(row.get("pitch")),
        "roll": _parse_float(row.get("roll")),
        "confidence": _parse_float(row.get("confidence")),
        "yaw_confidence": _parse_float(row.get("yaw_confidence")),
        "pitch_confidence": _parse_float(row.get("pitch_confidence")),
        "roll_confidence": _parse_float(row.get("roll_confidence")),
        "status": row.get("status") or "",
        "detected_line_count": _parse_int(row.get("detected_line_count")),
        "near_horizontal_count": _parse_int(row.get("near_horizontal_count")),
        "near_vertical_count": _parse_int(row.get("near_vertical_count")),
        "perspective_line_count": _parse_int(row.get("perspective_line_count")),
        "vanishing_point_candidate_count": _parse_int(row.get("vanishing_point_candidate_count")),
        "horizon_candidate_count": _parse_int(row.get("horizon_candidate_count")),
    }


def _evaluate_row(row: dict[str, Any], pose: PoseAngles) -> dict[str, Any]:
    yaw_error = _error(row["yaw"], pose.yaw_deg)
    pitch_error = _error(row["pitch"], pose.pitch_deg)
    roll_error = _error(row["roll"], pose.roll_deg)
    return {
        "frame_index": row["frame_index"],
        "time_sec": row["time_sec"],
        "pred_yaw": row["yaw"],
        "oxts_yaw": pose.yaw_deg,
        "yaw_error": yaw_error,
        "abs_yaw_error": abs(yaw_error) if yaw_error is not None else None,
        "pred_pitch": row["pitch"],
        "oxts_pitch": pose.pitch_deg,
        "pitch_error": pitch_error,
        "abs_pitch_error": abs(pitch_error) if pitch_error is not None else None,
        "pred_roll": row["roll"],
        "oxts_roll": pose.roll_deg,
        "roll_error": roll_error,
        "abs_roll_error": abs(roll_error) if roll_error is not None else None,
        "confidence": row["confidence"],
        "yaw_confidence": row["yaw_confidence"],
        "pitch_confidence": row["pitch_confidence"],
        "roll_confidence": row["roll_confidence"],
        "status": row["status"],
        "detected_line_count": row["detected_line_count"],
        "near_horizontal_count": row["near_horizontal_count"],
        "near_vertical_count": row["near_vertical_count"],
        "perspective_line_count": row["perspective_line_count"],
        "vanishing_point_candidate_count": row["vanishing_point_candidate_count"],
        "horizon_candidate_count": row["horizon_candidate_count"],
    }


def _plot_pred_vs_oxts(evaluated_rows: list[dict[str, Any]], angle: str, output_path: Path) -> None:
    frames = [row["frame_index"] for row in evaluated_rows]
    pred = [row[f"pred_{angle}"] for row in evaluated_rows]
    oxts = [row[f"oxts_{angle}"] for row in evaluated_rows]

    plt.figure(figsize=(11, 5))
    plt.plot(frames, pred, label=f"predicted {angle}", linewidth=1.6)
    plt.plot(frames, oxts, label=f"OXTS {angle}", linewidth=1.6)
    plt.title(f"{angle.upper()} predicted vs OXTS")
    plt.xlabel("frame_index")
    plt.ylabel(f"{angle} degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _plot_abs_error(evaluated_rows: list[dict[str, Any]], output_path: Path) -> None:
    frames = [row["frame_index"] for row in evaluated_rows]
    plt.figure(figsize=(11, 5))
    for angle in ("yaw", "pitch", "roll"):
        plt.plot(frames, [row[f"abs_{angle}_error"] for row in evaluated_rows], label=f"abs {angle} error", linewidth=1.4)
    plt.title("Absolute error by frame")
    plt.xlabel("frame_index")
    plt.ylabel("absolute error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _plot_confidence_vs_abs_error(evaluated_rows: list[dict[str, Any]], output_path: Path) -> None:
    plt.figure(figsize=(8, 6))
    for angle in ("yaw", "pitch", "roll"):
        points = [
            (row["confidence"], row[f"abs_{angle}_error"])
            for row in evaluated_rows
            if row["confidence"] is not None and row[f"abs_{angle}_error"] is not None
        ]
        if points:
            xs, ys = zip(*points)
            plt.scatter(xs, ys, s=18, alpha=0.65, label=f"{angle} abs error")
    plt.title("Confidence vs absolute error")
    plt.xlabel("confidence")
    plt.ylabel("absolute error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _top_error_frames(evaluated_rows: list[dict[str, Any]], angle: str, limit: int) -> list[dict[str, Any]]:
    error_key = f"{angle}_error"
    abs_key = f"abs_{angle}_error"
    sorted_rows = sorted(
        (row for row in evaluated_rows if row[abs_key] is not None),
        key=lambda row: row[abs_key],
        reverse=True,
    )
    return [
        {
            "frame_index": row["frame_index"],
            "time_sec": row["time_sec"],
            "predicted_value": row[f"pred_{angle}"],
            "oxts_value": row[f"oxts_{angle}"],
            "error": row[error_key],
            "abs_error": row[abs_key],
            "confidence": row["confidence"],
            "detected_line_count": row["detected_line_count"],
            "perspective_line_count": row["perspective_line_count"],
            "vanishing_point_candidate_count": row["vanishing_point_candidate_count"],
            "horizon_candidate_count": row["horizon_candidate_count"],
            "status": row["status"],
        }
        for row in sorted_rows[:limit]
    ]


def _valid_abs_errors(evaluated_rows: list[dict[str, Any]], angle: str) -> list[float]:
    return [row[f"abs_{angle}_error"] for row in evaluated_rows if row[f"abs_{angle}_error"] is not None]


def _valid_errors(evaluated_rows: list[dict[str, Any]], angle: str) -> list[float]:
    return [row[f"{angle}_error"] for row in evaluated_rows if row[f"{angle}_error"] is not None]


def _mean_abs(evaluated_rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _valid_abs_errors(evaluated_rows, angle)
    return mean(values) if values else None


def _median_abs(evaluated_rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _valid_abs_errors(evaluated_rows, angle)
    return median(values) if values else None


def _max_abs(evaluated_rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _valid_abs_errors(evaluated_rows, angle)
    return max(values) if values else None


def _rmse(evaluated_rows: list[dict[str, Any]], angle: str) -> float | None:
    values = _valid_errors(evaluated_rows, angle)
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def _error(predicted: float | None, expected: float) -> float | None:
    if predicted is None:
        return None
    return predicted - expected


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate video pose timeline against KITTI OXTS poses.")
    parser.add_argument("--pose-csv", type=Path, default=Path("outputs/video_pose/pose_timeline.csv"))
    parser.add_argument("--oxts-dir", type=Path, default=Path("tools/input/oxts"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/video_pose/evaluation"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        outputs = run_evaluation(args.pose_csv, args.oxts_dir, args.output_dir)
    except Exception as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote comparison CSV: {outputs.comparison_csv}")
    print(f"Wrote summary JSON: {outputs.summary_json}")
    print(f"Wrote worst frames CSV: {outputs.worst_frames_csv}")
    for path in outputs.plot_paths.values():
        print(f"Wrote plot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
