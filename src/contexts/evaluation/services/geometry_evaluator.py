from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.contexts.evaluation.domain.evaluation_result import EvaluationOutputs
from src.contexts.evaluation.domain.pose_record import PoseAngles
from src.contexts.evaluation.services.oxts_loader import load_poses
from src.contexts.evaluation.services import metrics as shared_metrics
from src.contexts.evaluation.services.rotation_error import geodesic_error_deg, signed_angle_error, zyx_rotation_matrix
from src.shared.output_contract import ANGLE_UNIT, ROTATION_ORDER, EvaluationArtifacts, resolve_legacy_artifact, validate_rotation_contract


EVALUATION_COLUMNS = [
    "sample_index",
    "pipeline",
    "pose_type",
    "source_frame_index",
    "prediction_valid",
    "warnings",
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
    "geodesic_error_deg",
    "pose_valid",
    "within_theta",
    "yaw_source",
    "comparison_ready",
    "pose_semantics",
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


def read_pose_timeline(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        validate_rotation_contract(row)
    return [_parse_pose_row(row) for row in rows]


def evaluate_rows(
    pose_rows: list[dict[str, Any]], oxts_poses: list[PoseAngles]
) -> list[dict[str, Any]]:
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
    *,
    theta_deg: float = 3.0,
    save_plots: bool = False,
    save_worst_frames: bool = False,
) -> EvaluationOutputs:
    if theta_deg <= 0:
        raise ValueError("theta_deg must be greater than zero.")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = EvaluationArtifacts(output_dir)
    comparison_csv = artifacts.per_frame
    summary_json = artifacts.summary
    report_md = artifacts.report

    for row in evaluated_rows:
        row["within_theta"] = bool(
            row.get("pose_valid") and row["geodesic_error_deg"] <= theta_deg
        )
    _write_csv(comparison_csv, evaluated_rows, EVALUATION_COLUMNS)
    summary = build_summary(evaluated_rows, theta_deg=theta_deg)
    summary_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    report_md.write_text(render_report(summary), encoding="utf-8")
    worst_frames_csv = None
    if save_worst_frames:
        worst_frames_csv = artifacts.worst_frames
        _write_csv(
            worst_frames_csv,
            build_worst_frames(evaluated_rows, limit=10),
            WORST_COLUMNS,
        )
    plot_paths = write_plots(evaluated_rows, output_dir) if save_plots else {}
    return EvaluationOutputs(
        comparison_csv=comparison_csv,
        summary_json=summary_json,
        report_md=report_md,
        worst_frames_csv=worst_frames_csv,
        plot_paths=plot_paths,
    )


def build_summary(
    evaluated_rows: list[dict[str, Any]], theta_deg: float = 3.0
) -> dict[str, Any]:
    geodesic_errors = _values(evaluated_rows, "geodesic_error_deg")
    valid_count = len(geodesic_errors)
    correct_count = sum(error <= theta_deg for error in geodesic_errors)
    strict_comparison_ready = bool(valid_count) and all(
        row.get("comparison_ready") for row in evaluated_rows if row.get("pose_valid")
    )
    return {
        "schema_version": "2.0",
        "pipeline": "geometry",
        "evaluation_type": "reference_based_pose_evaluation",
        "pose_type": "single_frame_orientation",
        "reference_frame": "camera_image_geometry",
        "rotation_order": ROTATION_ORDER,
        "unit": ANGLE_UNIT,
        "comparison_ready": strict_comparison_ready,
        "evaluation_method": "uncalibrated_geometry_axis_diagnostics",
        "prediction_reference_frame": "camera_image_geometry",
        "ground_truth_reference_frame": "vehicle_world_heading",
        "extrinsics_applied": False,
        "relative_rotation_method": None,
        "comparison_type": "geometry_pose_vs_oxts_absolute_pose",
        "strict_pose_comparison_ready": strict_comparison_ready,
        "diagnostic_only": not strict_comparison_ready,
        "warnings": [] if strict_comparison_ready else [
            "raw_geometry_yaw_and_oxts_absolute_heading_do_not_share_coordinate_semantics"
        ],
        "comparison_warning": None
        if strict_comparison_ready
        else "raw_geometry_yaw_and_oxts_absolute_heading_do_not_share_coordinate_semantics",
        "total_rows": len(evaluated_rows),
        "selected_metrics": {
            "theta_deg": theta_deg,
            "precision_at_theta": compute_precision_at_theta(evaluated_rows, theta_deg),
            "recall_at_theta": compute_recall_at_theta(evaluated_rows, theta_deg),
            "geodesic_mae_deg": compute_geodesic_mae(evaluated_rows),
            "p95_error_deg": compute_p95_error(evaluated_rows),
            "jitter_deg": compute_jitter(evaluated_rows),
            "valid_prediction_count": valid_count,
            "correct_prediction_count": correct_count,
            "reference_count": len(evaluated_rows),
        },
        "diagnostic_axis_metrics": {
            "pitch_mae_deg": _mean_abs(evaluated_rows, "pitch"),
            "pitch_rmse_deg": _rmse(evaluated_rows, "pitch"),
            "roll_mae_deg": _mean_abs(evaluated_rows, "roll"),
            "roll_rmse_deg": _rmse(evaluated_rows, "roll"),
        },
        "legacy_diagnostic_metrics": {
            "warning": "raw geometry yaw is not calibrated absolute heading",
            "selected_metrics": {
                "theta_deg": theta_deg,
                "precision_at_theta": compute_precision_at_theta(evaluated_rows, theta_deg),
                "recall_at_theta": compute_recall_at_theta(evaluated_rows, theta_deg),
                "geodesic_mae_deg": compute_geodesic_mae(evaluated_rows),
                "p95_error_deg": compute_p95_error(evaluated_rows),
                "jitter_deg": compute_jitter(evaluated_rows),
            },
        },
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


def build_worst_frames(
    evaluated_rows: list[dict[str, Any]], limit: int = 10
) -> list[dict[str, Any]]:
    worst: list[dict[str, Any]] = []
    for metric in ("yaw", "pitch", "roll"):
        for rank, row in enumerate(
            _top_error_frames(evaluated_rows, metric, limit), start=1
        ):
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
                    "vanishing_point_candidate_count": row[
                        "vanishing_point_candidate_count"
                    ],
                    "horizon_candidate_count": row["horizon_candidate_count"],
                }
            )
    return worst


def write_plots(
    evaluated_rows: list[dict[str, Any]], output_dir: Path
) -> dict[str, Path]:
    output_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
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


def render_report(summary: dict[str, Any]) -> str:
    metrics = summary["selected_metrics"]
    warning = summary.get("comparison_warning") or "none"
    return "\n".join(
        [
            "# Geometry Pose Evaluation",
            "",
            f"- Rotation order: {summary['rotation_order']}",
            f"- Unit: {summary['unit']}",
            "",
            "## Diagnostic Semantics",
            "",
            f"- Evaluation method: {summary['evaluation_method']}",
            f"- Comparison ready: {summary['comparison_ready']}",
            f"- Diagnostic only: {summary['diagnostic_only']}",
            "- Raw geometry yaw is excluded from any calibrated absolute-heading accuracy claim.",
            "",
            "## Pitch / Roll Diagnostic Metrics",
            "",
            f"- Pitch MAE: {_fmt(summary['diagnostic_axis_metrics']['pitch_mae_deg'])} deg",
            f"- Pitch RMSE: {_fmt(summary['diagnostic_axis_metrics']['pitch_rmse_deg'])} deg",
            f"- Roll MAE: {_fmt(summary['diagnostic_axis_metrics']['roll_mae_deg'])} deg",
            f"- Roll RMSE: {_fmt(summary['diagnostic_axis_metrics']['roll_rmse_deg'])} deg",
            "",
            "## Legacy 3D Diagnostic (Not Formal Accuracy)",
            "",
            f"- Precision@{metrics['theta_deg']:.2f} deg: {_fmt(metrics['precision_at_theta'])}",
            f"- Recall@{metrics['theta_deg']:.2f} deg: {_fmt(metrics['recall_at_theta'])}",
            f"- Geodesic MAE: {_fmt(metrics['geodesic_mae_deg'])} deg",
            f"- P95 geodesic error: {_fmt(metrics['p95_error_deg'])} deg",
            f"- Error jitter: {_fmt(metrics['jitter_deg'])} deg",
            "",
            "## Interpretation",
            "",
            f"- Strict pose comparison ready: {summary['strict_pose_comparison_ready']}",
            f"- Diagnostic only: {summary['diagnostic_only']}",
            f"- Comparison warning: `{warning}`",
            "",
            "Raw single-frame vanishing-point yaw must not be treated as calibrated OXTS absolute heading accuracy.",
        ]
    )


def run_evaluation(
    pose_csv: Path,
    oxts_dir: Path,
    output_dir: Path,
    *,
    theta_deg: float = 3.0,
    save_plots: bool = False,
    save_worst_frames: bool = False,
) -> EvaluationOutputs:
    pose_rows = read_pose_timeline(resolve_legacy_artifact(pose_csv))
    oxts_poses = load_poses(oxts_dir)
    evaluated_rows = evaluate_rows(pose_rows, oxts_poses)
    return write_evaluation_outputs(
        evaluated_rows,
        output_dir,
        theta_deg=theta_deg,
        save_plots=save_plots,
        save_worst_frames=save_worst_frames,
    )


def _parse_pose_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "sample_index": int(row.get("sample_index") or 0),
        "frame_index": int(row.get("source_frame_index") or row["frame_index"]),
        "time_sec": _parse_float(row.get("timestamp_sec") or row.get("time_sec")),
        "yaw": _parse_float(row.get("yaw_deg") or row.get("yaw")),
        "pitch": _parse_float(row.get("pitch_deg") or row.get("pitch")),
        "roll": _parse_float(row.get("roll_deg") or row.get("roll")),
        "calibrated_heading_yaw": _parse_float(row.get("calibrated_heading_yaw")),
        "comparison_ready": _parse_bool(row.get("comparison_ready")),
        "pose_semantics": row.get("pose_semantics") or "",
        "confidence": _parse_float(row.get("confidence")),
        "yaw_confidence": _parse_float(row.get("yaw_confidence")),
        "pitch_confidence": _parse_float(row.get("pitch_confidence")),
        "roll_confidence": _parse_float(row.get("roll_confidence")),
        "status": row.get("status") or "",
        "detected_line_count": _parse_int(row.get("detected_line_count")),
        "near_horizontal_count": _parse_int(row.get("near_horizontal_count")),
        "near_vertical_count": _parse_int(row.get("near_vertical_count")),
        "perspective_line_count": _parse_int(row.get("perspective_line_count")),
        "vanishing_point_candidate_count": _parse_int(
            row.get("vanishing_point_candidate_count")
        ),
        "horizon_candidate_count": _parse_int(row.get("horizon_candidate_count")),
    }


def _evaluate_row(row: dict[str, Any], pose: PoseAngles) -> dict[str, Any]:
    use_calibrated_yaw = bool(
        row.get("comparison_ready") and row.get("calibrated_heading_yaw") is not None
    )
    predicted_yaw = row["calibrated_heading_yaw"] if use_calibrated_yaw else row["yaw"]
    yaw_error = _error(predicted_yaw, pose.yaw_deg)
    pitch_error = _error(row["pitch"], pose.pitch_deg)
    roll_error = _error(row["roll"], pose.roll_deg)
    pose_valid = (
        predicted_yaw is not None
        and row["pitch"] is not None
        and row["roll"] is not None
    )
    geodesic_error = (
        _rotation_geodesic_error_deg(
            (predicted_yaw, row["pitch"], row["roll"]),
            (pose.yaw_deg, pose.pitch_deg, pose.roll_deg),
        )
        if pose_valid
        else None
    )
    return {
        "sample_index": int(row.get("sample_index") or 0),
        "pipeline": "geometry",
        "pose_type": "single_frame_orientation",
        "source_frame_index": row["frame_index"],
        "prediction_valid": pose_valid,
        "warnings": "",
        "frame_index": row["frame_index"],
        "time_sec": row["time_sec"],
        "pred_yaw": predicted_yaw,
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
        "geodesic_error_deg": geodesic_error,
        "pose_valid": pose_valid,
        "within_theta": None,
        "yaw_source": "calibrated_heading_yaw"
        if use_calibrated_yaw
        else "image_geometry_yaw",
        "comparison_ready": use_calibrated_yaw,
        "pose_semantics": row.get("pose_semantics") or "",
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


def _plot_pred_vs_oxts(
    evaluated_rows: list[dict[str, Any]], angle: str, output_path: Path
) -> None:
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
        plt.plot(
            frames,
            [row[f"abs_{angle}_error"] for row in evaluated_rows],
            label=f"abs {angle} error",
            linewidth=1.4,
        )
    plt.title("Absolute error by frame")
    plt.xlabel("frame_index")
    plt.ylabel("absolute error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()


def _plot_confidence_vs_abs_error(
    evaluated_rows: list[dict[str, Any]], output_path: Path
) -> None:
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


def _top_error_frames(
    evaluated_rows: list[dict[str, Any]], angle: str, limit: int
) -> list[dict[str, Any]]:
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
    return [
        row[f"abs_{angle}_error"]
        for row in evaluated_rows
        if row[f"abs_{angle}_error"] is not None
    ]


def _valid_errors(evaluated_rows: list[dict[str, Any]], angle: str) -> list[float]:
    return [
        row[f"{angle}_error"]
        for row in evaluated_rows
        if row[f"{angle}_error"] is not None
    ]


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


def compute_precision_at_theta(
    rows: list[dict[str, Any]], theta_deg: float
) -> float | None:
    return shared_metrics.precision_at_theta(rows, theta_deg)


def compute_recall_at_theta(
    rows: list[dict[str, Any]], theta_deg: float
) -> float | None:
    return shared_metrics.recall_at_theta(rows, theta_deg)


def compute_geodesic_mae(rows: list[dict[str, Any]]) -> float | None:
    return shared_metrics.geodesic_mae(rows)


def compute_p95_error(rows: list[dict[str, Any]]) -> float | None:
    return shared_metrics.p95_error(rows)


def compute_jitter(rows: list[dict[str, Any]]) -> float | None:
    return shared_metrics.error_jitter(rows)


def _rotation_geodesic_error_deg(
    predicted_ypr: tuple[float, float, float],
    expected_ypr: tuple[float, float, float],
) -> float:
    return geodesic_error_deg(predicted_ypr, expected_ypr)


def _zyx_rotation_matrix(
    yaw_deg: float, pitch_deg: float, roll_deg: float
) -> np.ndarray:
    return zyx_rotation_matrix(yaw_deg, pitch_deg, roll_deg)


def _values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _error(predicted: float | None, expected: float) -> float | None:
    return signed_angle_error(predicted, expected)


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _parse_bool(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"true", "1", "yes"})


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
