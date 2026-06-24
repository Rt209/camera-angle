from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.contexts.evaluation.domain.evaluation_result import EvaluationOutputs
from src.contexts.evaluation.domain.pose_record import PoseAngles
from src.contexts.evaluation.services.oxts_loader import load_poses
from src.contexts.evaluation.services import metrics as shared_metrics
from src.contexts.evaluation.services.rotation_error import (
    angle_delta,
    camera_motion_relative_rotation_zyx,
    conjugate_vehicle_delta_to_camera,
    geodesic_error_deg,
    rotation_matrix_to_pose_angles,
    signed_angle_error,
    zyx_rotation_matrix,
)
from src.shared.output_contract import ANGLE_UNIT, ROTATION_ORDER, EvaluationArtifacts, validate_rotation_contract


COMPARISON_COLUMNS = [
    "sample_index",
    "pipeline",
    "pose_type",
    "source_frame_index_prev",
    "source_frame_index_curr",
    "prediction_valid",
    "status",
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
    "legacy_oxts_relative_yaw",
    "legacy_oxts_relative_pitch",
    "legacy_oxts_relative_roll",
    "roll_error",
    "abs_roll_error",
    "geodesic_error_deg",
    "raw_pred_relative_yaw",
    "raw_pred_relative_pitch",
    "raw_pred_relative_roll",
    "raw_geodesic_error_deg",
    "pose_valid",
    "within_theta",
    "tracked_point_count",
    "inlier_count",
    "inlier_ratio",
    "confidence",
    "warnings",
]


OpticalFlowPoseEvaluationOutputs = EvaluationOutputs


def run_evaluation(
    pose_json: Path,
    oxts_dir: Path,
    output_dir: Path,
    *,
    theta_deg: float = 1.0,
    save_plots: bool = False,
    save_worst_frames: bool = False,
    camera_to_vehicle_rotation: np.ndarray | None = None,
    extrinsics_source: str | None = None,
) -> OpticalFlowPoseEvaluationOutputs:
    if theta_deg <= 0:
        raise ValueError("theta_deg must be greater than zero.")
    pose_metadata = read_pose_metadata(pose_json)
    pose_rows = _read_pose_json(pose_json)
    oxts_poses = load_poses(oxts_dir)
    comparison = evaluate_rows(
        pose_rows, oxts_poses, camera_to_vehicle_rotation
    )
    return write_evaluation_outputs(
        comparison,
        output_dir,
        theta_deg=theta_deg,
        save_plots=save_plots,
        save_worst_frames=save_worst_frames,
        extrinsics_applied=camera_to_vehicle_rotation is not None,
        intrinsics_calibrated=bool(pose_metadata.get("intrinsics_calibrated")),
        extrinsics_source=extrinsics_source,
    )


def write_evaluation_outputs(
    comparison: list[dict[str, Any]],
    output_dir: Path,
    *,
    theta_deg: float = 1.0,
    save_plots: bool = False,
    save_worst_frames: bool = False,
    extrinsics_applied: bool = False,
    intrinsics_calibrated: bool = False,
    extrinsics_source: str | None = None,
) -> OpticalFlowPoseEvaluationOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = EvaluationArtifacts(output_dir)
    comparison_csv = artifacts.per_frame
    summary_json = artifacts.summary
    report_md = artifacts.report

    for row in comparison:
        row["within_theta"] = bool(
            row["pose_valid"] and row["geodesic_error_deg"] <= theta_deg
        )
    _write_csv(comparison_csv, comparison, COMPARISON_COLUMNS)
    summary = build_summary(
        comparison,
        theta_deg=theta_deg,
        extrinsics_applied=extrinsics_applied,
        intrinsics_calibrated=intrinsics_calibrated,
        extrinsics_source=extrinsics_source,
    )
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    worst_frames_csv = None
    if save_worst_frames:
        worst_frames_csv = artifacts.worst_frames
        _write_csv(
            worst_frames_csv,
            build_worst_frames(comparison),
            ["rank", "metric", *COMPARISON_COLUMNS],
        )
    plot_paths = write_plots(comparison, output_dir) if save_plots else {}
    report_md.write_text(
        render_report(summary, comparison, plot_paths), encoding="utf-8"
    )
    return OpticalFlowPoseEvaluationOutputs(
        comparison_csv, summary_json, report_md, worst_frames_csv, plot_paths
    )


def evaluate_rows(
    pose_rows: list[dict[str, Any]],
    oxts_poses: list[PoseAngles],
    camera_to_vehicle_rotation: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    comparison = []
    for row in pose_rows:
        frame_index = int(row.get("source_frame_index_curr") or row["frame_index"])
        previous_frame_index = int(row.get("source_frame_index_prev", frame_index - 1))
        if frame_index <= 0 or frame_index >= len(oxts_poses):
            continue
        oxts_abs = oxts_poses[frame_index]
        if previous_frame_index < 0 or previous_frame_index >= len(oxts_poses):
            continue
        oxts_prev = oxts_poses[previous_frame_index]
        vehicle_delta = camera_motion_relative_rotation_zyx(
            (oxts_prev.yaw_deg, oxts_prev.pitch_deg, oxts_prev.roll_deg),
            (oxts_abs.yaw_deg, oxts_abs.pitch_deg, oxts_abs.roll_deg),
        )
        comparison_delta = (
            conjugate_vehicle_delta_to_camera(vehicle_delta, camera_to_vehicle_rotation)
            if camera_to_vehicle_rotation is not None
            else vehicle_delta
        )
        rel_yaw, rel_pitch, rel_roll = rotation_matrix_to_pose_angles(comparison_delta)
        rel = PoseAngles(rel_yaw, rel_pitch, rel_roll)
        legacy_rel = PoseAngles(
            yaw_deg=_angle_delta(oxts_abs.yaw_deg, oxts_prev.yaw_deg),
            pitch_deg=_angle_delta(oxts_abs.pitch_deg, oxts_prev.pitch_deg),
            roll_deg=_angle_delta(oxts_abs.roll_deg, oxts_prev.roll_deg),
        )
        pred_yaw = _parse_float(row.get("yaw_deg"))
        pred_pitch = _parse_float(row.get("pitch_deg"))
        pred_roll = _parse_float(row.get("roll_deg"))
        raw_yaw = _parse_float(row.get("raw_yaw_deg"))
        raw_pitch = _parse_float(row.get("raw_pitch_deg"))
        raw_roll = _parse_float(row.get("raw_roll_deg"))
        yaw_error = _error(pred_yaw, rel.yaw_deg)
        pitch_error = _error(pred_pitch, rel.pitch_deg)
        roll_error = _error(pred_roll, rel.roll_deg)
        pose_valid = (
            pred_yaw is not None and pred_pitch is not None and pred_roll is not None
        )
        geodesic_error = (
            _rotation_geodesic_error_deg(
                (pred_yaw, pred_pitch, pred_roll),
                (rel.yaw_deg, rel.pitch_deg, rel.roll_deg),
            )
            if pose_valid
            else None
        )
        raw_geodesic_error = (
            _rotation_geodesic_error_deg((raw_yaw, raw_pitch, raw_roll),
                                         (rel.yaw_deg, rel.pitch_deg, rel.roll_deg))
            if raw_yaw is not None and raw_pitch is not None and raw_roll is not None else None
        )
        comparison.append(
            {
                "sample_index": int(row.get("sample_index") or len(comparison)),
                "pipeline": "optical",
                "pose_type": "frame_to_frame_relative_rotation",
                "source_frame_index_prev": previous_frame_index,
                "source_frame_index_curr": frame_index,
                "prediction_valid": pose_valid,
                "status": row.get("status") or ("valid" if pose_valid else "failed"),
                "frame_index": frame_index,
                "timestamp_sec": _parse_float(row.get("timestamp_sec_curr") or row.get("timestamp_sec")),
                "pred_relative_yaw": pred_yaw,
                "oxts_absolute_yaw": oxts_abs.yaw_deg,
                "oxts_relative_yaw": rel.yaw_deg,
                "yaw_error": yaw_error,
                "abs_yaw_error": abs(yaw_error) if yaw_error is not None else None,
                "pred_relative_pitch": pred_pitch,
                "oxts_absolute_pitch": oxts_abs.pitch_deg,
                "oxts_relative_pitch": rel.pitch_deg,
                "pitch_error": pitch_error,
                "abs_pitch_error": abs(pitch_error)
                if pitch_error is not None
                else None,
                "pred_relative_roll": pred_roll,
                "oxts_absolute_roll": oxts_abs.roll_deg,
                "oxts_relative_roll": rel.roll_deg,
                "legacy_oxts_relative_yaw": legacy_rel.yaw_deg,
                "legacy_oxts_relative_pitch": legacy_rel.pitch_deg,
                "legacy_oxts_relative_roll": legacy_rel.roll_deg,
                "roll_error": roll_error,
                "abs_roll_error": abs(roll_error) if roll_error is not None else None,
                "geodesic_error_deg": geodesic_error,
                "raw_pred_relative_yaw": raw_yaw,
                "raw_pred_relative_pitch": raw_pitch,
                "raw_pred_relative_roll": raw_roll,
                "raw_geodesic_error_deg": raw_geodesic_error,
                "pose_valid": pose_valid,
                "within_theta": None,
                "tracked_point_count": int(row.get("tracked_point_count") or 0),
                "inlier_count": int(row.get("inlier_count") or 0),
                "inlier_ratio": _parse_float(row.get("inlier_ratio")),
                "confidence": _parse_float(row.get("confidence")),
                "warnings": "|".join(row.get("warnings") or []),
            }
        )
    return comparison


def build_summary(
    rows: list[dict[str, Any]],
    theta_deg: float = 1.0,
    *,
    extrinsics_applied: bool = False,
    intrinsics_calibrated: bool = False,
    extrinsics_source: str | None = None,
) -> dict[str, Any]:
    geodesic_errors = _values(rows, "geodesic_error_deg")
    valid_count = len(geodesic_errors)
    correct_count = sum(error <= theta_deg for error in geodesic_errors)
    raw_errors = _values(rows, "raw_geodesic_error_deg")
    statuses = [str(row.get("status") or "failed") for row in rows]
    comparison_ready = extrinsics_applied and intrinsics_calibrated
    warnings = []
    if not intrinsics_calibrated:
        warnings.extend(["intrinsics_not_calibrated", "approximate_K_used"])
    if not extrinsics_applied:
        warnings.append("camera_vehicle_extrinsics_missing")
    if not comparison_ready:
        warnings.append("pose_for_debug_only")
    return {
        "schema_version": "2.0",
        "pipeline": "optical",
        "evaluation_type": "reference_based_pose_evaluation",
        "pose_type": "frame_to_frame_relative_rotation",
        "reference_frame": "camera",
        "rotation_order": ROTATION_ORDER,
        "unit": ANGLE_UNIT,
        "comparison_ready": comparison_ready,
        "diagnostic_only": not comparison_ready,
        "evaluation_method": (
            "calibrated_camera_frame_relative_pose"
            if comparison_ready
            else "rotation_matrix_relative_pose_diagnostic"
        ),
        "prediction_reference_frame": "camera",
        "ground_truth_reference_frame": "vehicle_body",
        "intrinsics_calibrated": intrinsics_calibrated,
        "extrinsics_applied": extrinsics_applied,
        "extrinsics_source": extrinsics_source,
        "relative_rotation_method": "R_current_transpose_times_R_previous_ZYX_camera_motion",
        "warnings": warnings,
        "comparison_type": (
            "camera_relative_rotation_vs_camera_transformed_oxts_rotation"
            if extrinsics_applied
            else "camera_relative_rotation_vs_vehicle_relative_rotation_without_extrinsics"
        ),
        "calibrated_pose_result": intrinsics_calibrated,
        "prototype_warnings": warnings,
        "total_rows": len(rows),
        "selected_metrics": {
            "theta_deg": theta_deg,
            "precision_at_theta": compute_precision_at_theta(rows, theta_deg),
            "recall_at_theta": compute_recall_at_theta(rows, theta_deg),
            "geodesic_mae_deg": compute_geodesic_mae(rows),
            "p95_error_deg": compute_p95_error(rows),
            "jitter_deg": compute_jitter(rows),
            "valid_prediction_count": valid_count,
            "correct_prediction_count": correct_count,
            "reference_count": len(rows),
        },
        "pose_status_counts": {
            "accepted": sum(status in {"accepted", "valid"} for status in statuses),
            "rejected": sum(status == "rejected" for status in statuses),
            "failed": sum(status == "failed" for status in statuses),
        },
        "raw_metrics": {
            "valid_prediction_count": len(raw_errors),
            "geodesic_mae_deg": mean(raw_errors) if raw_errors else None,
            "catastrophic_error_threshold_deg": 30.0,
            "catastrophic_error_count": sum(error > 30.0 for error in raw_errors),
        },
        "accepted_metrics": {
            "valid_prediction_count": valid_count,
            "geodesic_mae_deg": compute_geodesic_mae(rows),
            "catastrophic_error_threshold_deg": 30.0,
            "catastrophic_error_count": sum(error > 30.0 for error in geodesic_errors),
            "recall_denominator": len(rows),
        },
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


def build_worst_frames(
    rows: list[dict[str, Any]], limit: int = 10
) -> list[dict[str, Any]]:
    worst = []
    for metric in ("yaw", "pitch", "roll"):
        for rank, row in enumerate(_top_error_frames(rows, metric, limit), start=1):
            full = next(
                source for source in rows if source["frame_index"] == row["frame_index"]
            )
            worst.append({"rank": rank, "metric": metric, **full})
    return worst


def write_plots(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    output_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
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


def render_report(
    summary: dict[str, Any], rows: list[dict[str, Any]], plot_paths: dict[str, Path]
) -> str:
    metrics = summary["selected_metrics"]
    lines = [
        (
            "# Optical Flow Calibrated Pose vs KITTI OXTS Evaluation"
            if summary["comparison_ready"]
            else "# Optical Flow Uncalibrated Pose vs KITTI OXTS Evaluation"
        ),
        "",
        "This report compares the optical-flow prototype's frame-to-frame relative yaw/pitch/roll against KITTI OXTS frame-to-frame angle deltas.",
        "",
        (
            "KITTI camera intrinsics and camera-to-vehicle rotation were applied; both rotations are compared in the rectified camera frame."
            if summary["comparison_ready"]
            else "Important caveat: missing intrinsics or camera-to-vehicle extrinsics keep this comparison diagnostic-only."
        ),
        "",
        "## Summary",
        "",
        f"- Rotation order: {summary['rotation_order']}",
        f"- Unit: {summary['unit']}",
        f"- Rows compared: {summary['total_rows']}",
        f"- Evaluation method: {summary['evaluation_method']}",
        f"- Comparison ready: {summary['comparison_ready']}",
        f"- Diagnostic only: {summary['diagnostic_only']}",
        f"- Prediction frame: {summary['prediction_reference_frame']}",
        f"- Ground truth frame: {summary['ground_truth_reference_frame']}",
        f"- Extrinsics applied: {summary['extrinsics_applied']}",
        f"- Intrinsics calibrated: {summary['intrinsics_calibrated']}",
        f"- Extrinsics source: {summary['extrinsics_source']}",
        f"- Relative rotation: {summary['relative_rotation_method']}",
        f"- Precision@{_fmt(metrics['theta_deg'])} deg: {_fmt(metrics['precision_at_theta'])}",
        f"- Recall@{_fmt(metrics['theta_deg'])} deg: {_fmt(metrics['recall_at_theta'])}",
        f"- Geodesic MAE: {_fmt(metrics['geodesic_mae_deg'])} deg",
        f"- P95 geodesic error: {_fmt(metrics['p95_error_deg'])} deg",
        f"- Error jitter: {_fmt(metrics['jitter_deg'])} deg",
        f"- Mean inlier ratio: {_fmt(summary['mean_inlier_ratio'])}",
        f"- Mean confidence: {_fmt(summary['mean_confidence'])}",
        f"- Accepted / rejected / failed: {summary['pose_status_counts']['accepted']} / {summary['pose_status_counts']['rejected']} / {summary['pose_status_counts']['failed']}",
        f"- Raw / accepted catastrophic errors (>30 deg): {summary['raw_metrics']['catastrophic_error_count']} / {summary['accepted_metrics']['catastrophic_error_count']}",
        f"- Mean abs yaw error: {_fmt(summary['mean_abs_yaw_error'])} deg",
        f"- Mean abs pitch error: {_fmt(summary['mean_abs_pitch_error'])} deg",
        f"- Mean abs roll error: {_fmt(summary['mean_abs_roll_error'])} deg",
        f"- RMSE yaw/pitch/roll: {_fmt(summary['rmse_yaw_error'])}, {_fmt(summary['rmse_pitch_error'])}, {_fmt(summary['rmse_roll_error'])} deg",
        "",
        "## Analysis",
        "",
        "- OXTS camera motion is computed as R_current.T @ R_previous to match OpenCV recoverPose's camera-1 to camera-2 rotation convention.",
        (
            "- Camera-to-vehicle extrinsics transform OXTS relative rotations into the rectified camera frame."
            if summary["extrinsics_applied"]
            else "- Camera-to-vehicle extrinsics were not supplied, so camera-frame prediction versus vehicle-frame ground truth is diagnostic-only and not a formal accuracy headline."
        ),
        (
            "- Calibrated camera intrinsics were used for Essential Matrix estimation."
            if summary["intrinsics_calibrated"]
            else "- Confidence remains damped because K is approximate; inlier ratio alone is not calibration quality."
        ),
        "- Large yaw errors usually indicate that approximate intrinsics, forward-motion degeneracy, or scene-depth variation is dominating the Essential Matrix solution.",
        "- Pitch and roll errors should be interpreted as relative-frame debug signals until a real calibration video provides camera intrinsics.",
        "",
        "## Worst Frames",
        "",
    ]
    if plot_paths:
        lines[lines.index("## Analysis") : lines.index("## Analysis")] = [
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
    validate_rotation_contract(data)
    rows = list(data["frames"])
    for row in rows:
        validate_rotation_contract(row)
    return rows


def read_pose_json(path: Path) -> list[dict[str, Any]]:
    return _read_pose_json(path)


def read_pose_metadata(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_rotation_contract(data)
    return data


def _plot_relative(rows: list[dict[str, Any]], angle: str, output_path: Path) -> None:
    frames = [row["frame_index"] for row in rows]
    plt.figure(figsize=(11, 5))
    plt.plot(
        frames,
        [row[f"pred_relative_{angle}"] for row in rows],
        label=f"pred relative {angle}",
        linewidth=1.4,
    )
    plt.plot(
        frames,
        [row[f"oxts_relative_{angle}"] for row in rows],
        label=f"OXTS delta {angle}",
        linewidth=1.4,
    )
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
        plt.plot(
            frames,
            [row[f"abs_{angle}_error"] for row in rows],
            label=f"abs {angle} error",
            linewidth=1.3,
        )
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


def _top_error_frames(
    rows: list[dict[str, Any]], angle: str, limit: int
) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows, key=lambda row: row[f"abs_{angle}_error"] or -1, reverse=True
    )
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
    return angle_delta(current, previous)


def _rotation_geodesic_error_deg(
    predicted_ypr: tuple[float, float, float],
    expected_ypr: tuple[float, float, float],
) -> float:
    return geodesic_error_deg(predicted_ypr, expected_ypr)


def compute_precision_at_theta(
    rows: list[dict[str, Any]], theta_deg: float
) -> float | None:
    """Return correct valid predictions divided by all valid predictions."""
    return shared_metrics.precision_at_theta(rows, theta_deg)


def compute_recall_at_theta(
    rows: list[dict[str, Any]], theta_deg: float
) -> float | None:
    """Return correct predictions divided by all reference rows, including pose dropouts."""
    return shared_metrics.recall_at_theta(rows, theta_deg)


def compute_geodesic_mae(rows: list[dict[str, Any]]) -> float | None:
    return shared_metrics.geodesic_mae(rows)


def compute_p95_error(rows: list[dict[str, Any]]) -> float | None:
    return shared_metrics.p95_error(rows)


def compute_jitter(rows: list[dict[str, Any]]) -> float | None:
    """Return RMS frame-to-frame change of the rotation-error sequence."""
    return shared_metrics.error_jitter(rows)


def _zyx_rotation_matrix(
    yaw_deg: float, pitch_deg: float, roll_deg: float
) -> np.ndarray:
    return zyx_rotation_matrix(yaw_deg, pitch_deg, roll_deg)


def _compute_error_jitter(rows: list[dict[str, Any]]) -> float | None:
    valid_rows = [row for row in rows if row.get("pose_valid")]
    changes = []
    for previous, current in zip(valid_rows, valid_rows[1:]):
        if current["frame_index"] != previous["frame_index"] + 1:
            continue
        previous_error = (
            previous["yaw_error"],
            previous["pitch_error"],
            previous["roll_error"],
        )
        current_error = (
            current["yaw_error"],
            current["pitch_error"],
            current["roll_error"],
        )
        changes.append(_rotation_geodesic_error_deg(current_error, previous_error))
    return math.sqrt(mean(value * value for value in changes)) if changes else None


def _percentile(values: list[float], percentile: float) -> float | None:
    return float(np.percentile(values, percentile)) if values else None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _error(predicted: float | None, expected: float) -> float | None:
    return signed_angle_error(predicted, expected)


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
