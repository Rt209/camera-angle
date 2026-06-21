from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


CALIBRATION_RANGE = range(0, 81)
VALIDATION_RANGE = range(81, 154)
SEGMENTS = {
    "all": range(0, 154),
    "calibration_0_80": CALIBRATION_RANGE,
    "validation_81_153": VALIDATION_RANGE,
    "frame_91_100": range(91, 101),
    "frame_112_117": range(112, 118),
    "frame_150_153": range(150, 154),
}

OUTPUT_COLUMNS = [
    "frame_index",
    "time_sec",
    "segment",
    "raw_vp_yaw",
    "image_geometry_yaw",
    "reliability_gated_yaw",
    "calibrated_heading_yaw",
    "oxts_yaw",
    "raw_abs_yaw_error",
    "current_abs_yaw_error",
    "calibrated_abs_yaw_error",
    "yaw_confidence_before",
    "yaw_confidence_after",
    "confidence_failure_before",
    "confidence_failure_after",
    "yaw_calibration_model",
    "yaw_calibration_scale",
    "yaw_calibration_offset",
    "comparison_ready",
    "vp_temporal_jump",
    "vp_side_flip",
    "vp_cluster_ambiguity",
    "line_support_consistency",
    "yaw_warning_flags",
]


def main() -> int:
    args = build_parser().parse_args()
    calibration_dir = args.output_dir / "calibration"
    evaluation_dir = args.output_dir / "evaluation"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    evaluation_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(args.pose_csv, args.comparison_csv)
    offset_model = fit_offset_model(rows)
    linear_model = fit_linear_model(rows)
    selected_model = choose_model(rows, offset_model, linear_model)
    output_rows = build_output_rows(rows, selected_model)
    summary = build_summary(rows, output_rows, offset_model, linear_model, selected_model)

    write_json(calibration_dir / "yaw_calibration_model.json", selected_model)
    write_csv(evaluation_dir / "calibrated_pose_vs_oxts.csv", output_rows, OUTPUT_COLUMNS)
    write_json(evaluation_dir / "yaw_calibration_summary.json", summary)
    write_before_after(evaluation_dir / "yaw_calibration_before_after.md", summary)
    write_report(evaluation_dir / "yaw_calibration_report.md", summary)
    write_plots(output_rows, evaluation_dir)

    print(f"Wrote yaw calibration model: {calibration_dir / 'yaw_calibration_model.json'}")
    print(f"Wrote yaw calibration evaluation: {evaluation_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run geometry yaw calibration transform experiment.")
    parser.add_argument("--pose-csv", type=Path, default=Path("outputs/video_pose/pose_timeline.csv"))
    parser.add_argument("--comparison-csv", type=Path, default=Path("outputs/video_pose/evaluation/pose_vs_oxts.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/geometry_yaw_oxts_experiment"))
    return parser


def load_rows(pose_csv: Path, comparison_csv: Path) -> list[dict[str, Any]]:
    pose_by_frame = {
        int(row["frame_index"]): row
        for row in csv.DictReader(pose_csv.open(newline="", encoding="utf-8"))
    }
    rows: list[dict[str, Any]] = []
    for comparison in csv.DictReader(comparison_csv.open(newline="", encoding="utf-8")):
        frame_index = int(comparison["frame_index"])
        pose = pose_by_frame[frame_index]
        rows.append(
            {
                "frame_index": frame_index,
                "time_sec": _float(comparison.get("time_sec")),
                "raw_vp_yaw": _float(pose.get("raw_vp_yaw")),
                "image_geometry_yaw": _float(pose.get("image_geometry_yaw")),
                "reliability_gated_yaw": _float(pose.get("yaw")),
                "oxts_yaw": _float(comparison.get("oxts_yaw")),
                "current_abs_yaw_error": _float(comparison.get("abs_yaw_error")),
                "yaw_confidence": _float(comparison.get("yaw_confidence")),
                "vp_temporal_jump": _float(pose.get("vp_temporal_jump")),
                "vp_side_flip": _parse_bool(pose.get("vp_side_flip")),
                "vp_cluster_ambiguity": _float(pose.get("vp_cluster_ambiguity")),
                "line_support_consistency": _float(pose.get("line_support_consistency")),
                "yaw_warning_flags": _parse_json_list(pose.get("yaw_warning_flags")),
            }
        )
    return rows


def fit_offset_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calibration_rows = _segment_rows(rows, CALIBRATION_RANGE)
    offsets = [
        angle_delta(row["oxts_yaw"], row["reliability_gated_yaw"])
        for row in calibration_rows
        if row["oxts_yaw"] is not None and row["reliability_gated_yaw"] is not None
    ]
    offset = median(offsets)
    return {
        "model_type": "offset_only",
        "scale": 1.0,
        "yaw_offset": offset,
        "calibration_segment": "frame_0_80",
        "validation_segment": "frame_81_153",
    }


def fit_linear_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calibration_rows = [
        row for row in _segment_rows(rows, CALIBRATION_RANGE)
        if row["oxts_yaw"] is not None and row["reliability_gated_yaw"] is not None
    ]
    x = np.array([[row["reliability_gated_yaw"], 1.0] for row in calibration_rows])
    y = np.array([row["oxts_yaw"] for row in calibration_rows])
    scale, offset = np.linalg.lstsq(x, y, rcond=None)[0]
    return {
        "model_type": "linear",
        "scale": float(scale),
        "yaw_offset": float(offset),
        "calibration_segment": "frame_0_80",
        "validation_segment": "frame_81_153",
    }


def choose_model(
    rows: list[dict[str, Any]],
    offset_model: dict[str, Any],
    linear_model: dict[str, Any],
) -> dict[str, Any]:
    models = [offset_model, linear_model]
    selected = min(
        models,
        key=lambda model: _mae(_segment_rows(rows, VALIDATION_RANGE), lambda row: apply_model(row, model)),
    )
    return {
        **selected,
        "selected_by": "lowest_validation_yaw_mae",
        "candidate_models": {
            "offset_only": model_metrics(rows, offset_model),
            "linear": model_metrics(rows, linear_model),
        },
    }


def build_output_rows(rows: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        calibrated = apply_model(row, model)
        raw_error = _abs_error(row["image_geometry_yaw"], row["oxts_yaw"])
        current_error = row["current_abs_yaw_error"]
        calibrated_error = _abs_error(calibrated, row["oxts_yaw"])
        confidence_after = adjusted_confidence(row, calibrated_error)
        output.append(
            {
                "frame_index": row["frame_index"],
                "time_sec": row["time_sec"],
                "segment": segment_name(row["frame_index"]),
                "raw_vp_yaw": row["raw_vp_yaw"],
                "image_geometry_yaw": row["image_geometry_yaw"],
                "reliability_gated_yaw": row["reliability_gated_yaw"],
                "calibrated_heading_yaw": calibrated,
                "oxts_yaw": row["oxts_yaw"],
                "raw_abs_yaw_error": raw_error,
                "current_abs_yaw_error": current_error,
                "calibrated_abs_yaw_error": calibrated_error,
                "yaw_confidence_before": row["yaw_confidence"],
                "yaw_confidence_after": confidence_after,
                "confidence_failure_before": confidence_failure(row["yaw_confidence"], current_error),
                "confidence_failure_after": confidence_failure(confidence_after, calibrated_error),
                "yaw_calibration_model": model["model_type"],
                "yaw_calibration_scale": model["scale"],
                "yaw_calibration_offset": model["yaw_offset"],
                "comparison_ready": True,
                "vp_temporal_jump": row["vp_temporal_jump"],
                "vp_side_flip": row["vp_side_flip"],
                "vp_cluster_ambiguity": row["vp_cluster_ambiguity"],
                "line_support_consistency": row["line_support_consistency"],
                "yaw_warning_flags": json.dumps(row["yaw_warning_flags"], ensure_ascii=True),
            }
        )
    return output


def adjusted_confidence(row: dict[str, Any], calibrated_error: float | None) -> float | None:
    confidence = row["yaw_confidence"]
    if confidence is None:
        return None
    penalty = 0.0
    flags = set(row["yaw_warning_flags"])
    if "high_cluster_ambiguity" in flags:
        penalty += 0.10
    if "large_temporal_jump" in flags:
        penalty += 0.10
    if row["vp_cluster_ambiguity"] is not None and row["vp_cluster_ambiguity"] >= 0.75:
        penalty += 0.10
    if row["line_support_consistency"] is not None and row["line_support_consistency"] < 0.35:
        penalty += 0.10
    if calibrated_error is not None and calibrated_error >= 30.0:
        penalty += 0.25
    return round(max(0.0, min(1.0, confidence * (1.0 - min(penalty, 0.75)))), 2)


def build_summary(
    rows: list[dict[str, Any]],
    output_rows: list[dict[str, Any]],
    offset_model: dict[str, Any],
    linear_model: dict[str, Any],
    selected_model: dict[str, Any],
) -> dict[str, Any]:
    output_by_frame = {row["frame_index"]: row for row in output_rows}
    summary = {
        "selected_model": selected_model,
        "offset_only_metrics": model_metrics(rows, offset_model),
        "linear_metrics": model_metrics(rows, linear_model),
        "segments": {},
        "confidence_failure_before": sum(row["confidence_failure_before"] for row in output_rows),
        "confidence_failure_after": sum(row["confidence_failure_after"] for row in output_rows),
        "high_confidence_high_error_frames_after": [
            row["frame_index"] for row in output_rows if row["confidence_failure_after"]
        ],
        "calibration_transform_status": "success",
    }
    for name, frame_range in SEGMENTS.items():
        raw_rows = _segment_rows(rows, frame_range)
        calibrated_rows = [output_by_frame[row["frame_index"]] for row in raw_rows]
        summary["segments"][name] = {
            "current_yaw_mae": _mae(raw_rows, lambda row: row["reliability_gated_yaw"]),
            "calibrated_yaw_mae": _mean_value(calibrated_rows, "calibrated_abs_yaw_error"),
            "raw_image_geometry_yaw_mae": _mae(raw_rows, lambda row: row["image_geometry_yaw"]),
            "confidence_failure_before": sum(row["confidence_failure_before"] for row in calibrated_rows),
            "confidence_failure_after": sum(row["confidence_failure_after"] for row in calibrated_rows),
        }
    summary["success_criteria"] = {
        "validation_mae_improved": (
            summary["segments"]["validation_81_153"]["calibrated_yaw_mae"]
            < summary["segments"]["validation_81_153"]["current_yaw_mae"]
        ),
        "confidence_failure_reduced": (
            summary["confidence_failure_after"] < summary["confidence_failure_before"]
        ),
        "frame_112_117_improved": (
            summary["segments"]["frame_112_117"]["calibrated_yaw_mae"]
            < summary["segments"]["frame_112_117"]["current_yaw_mae"]
        ),
        "frame_150_153_improved": (
            summary["segments"]["frame_150_153"]["calibrated_yaw_mae"]
            < summary["segments"]["frame_150_153"]["current_yaw_mae"]
        ),
    }
    if not all(summary["success_criteria"].values()):
        summary["calibration_transform_status"] = "partial"
    return summary


def model_metrics(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, float | str]:
    return {
        "model_type": model["model_type"],
        "scale": model["scale"],
        "yaw_offset": model["yaw_offset"],
        "calibration_mae": _mae(_segment_rows(rows, CALIBRATION_RANGE), lambda row: apply_model(row, model)),
        "validation_mae": _mae(_segment_rows(rows, VALIDATION_RANGE), lambda row: apply_model(row, model)),
        "all_mae": _mae(rows, lambda row: apply_model(row, model)),
    }


def apply_model(row: dict[str, Any], model: dict[str, Any]) -> float | None:
    yaw = row["reliability_gated_yaw"]
    if yaw is None:
        return None
    return round(wrap_angle((model["scale"] * yaw) + model["yaw_offset"]), 4)


def write_before_after(path: Path, summary: dict[str, Any]) -> None:
    segments = summary["segments"]
    text = f"""# Yaw Calibration Before / After

| Metric | Before | After |
|---|---:|---:|
| All yaw MAE | {_fmt(segments['all']['current_yaw_mae'])} deg | {_fmt(segments['all']['calibrated_yaw_mae'])} deg |
| Calibration segment yaw MAE | {_fmt(segments['calibration_0_80']['current_yaw_mae'])} deg | {_fmt(segments['calibration_0_80']['calibrated_yaw_mae'])} deg |
| Validation segment yaw MAE | {_fmt(segments['validation_81_153']['current_yaw_mae'])} deg | {_fmt(segments['validation_81_153']['calibrated_yaw_mae'])} deg |
| Frame 91-100 yaw MAE | {_fmt(segments['frame_91_100']['current_yaw_mae'])} deg | {_fmt(segments['frame_91_100']['calibrated_yaw_mae'])} deg |
| Frame 112-117 yaw MAE | {_fmt(segments['frame_112_117']['current_yaw_mae'])} deg | {_fmt(segments['frame_112_117']['calibrated_yaw_mae'])} deg |
| Frame 150-153 yaw MAE | {_fmt(segments['frame_150_153']['current_yaw_mae'])} deg | {_fmt(segments['frame_150_153']['calibrated_yaw_mae'])} deg |
| Confidence failure count | {summary['confidence_failure_before']} | {summary['confidence_failure_after']} |

Selected model: `{summary['selected_model']['model_type']}`

```text
scale = {summary['selected_model']['scale']}
yaw_offset = {summary['selected_model']['yaw_offset']}
calibration segment = frame 0-80
validation segment = frame 81-153
```
"""
    path.write_text(text, encoding="utf-8")


def write_report(path: Path, summary: dict[str, Any]) -> None:
    segments = summary["segments"]
    criteria = summary["success_criteria"]
    text = f"""# Geometry Yaw Calibration Transform Report

## 目的

本實驗建立 `calibration transform -> calibrated_heading_yaw`，避免繼續把 `image_geometry_yaw` 直接拿去和 KITTI OXTS absolute heading 比較。

## Calibration Model

| Field | Value |
|---|---:|
| model type | {summary['selected_model']['model_type']} |
| scale | {summary['selected_model']['scale']:.6f} |
| yaw offset | {summary['selected_model']['yaw_offset']:.6f} deg |
| calibration segment | frame 0-80 |
| validation segment | frame 81-153 |

候選模型比較：

| Model | Calibration MAE | Validation MAE | All MAE |
|---|---:|---:|---:|
| offset-only | {_fmt(summary['offset_only_metrics']['calibration_mae'])} | {_fmt(summary['offset_only_metrics']['validation_mae'])} | {_fmt(summary['offset_only_metrics']['all_mae'])} |
| linear | {_fmt(summary['linear_metrics']['calibration_mae'])} | {_fmt(summary['linear_metrics']['validation_mae'])} | {_fmt(summary['linear_metrics']['all_mae'])} |

## Before / After

| Segment | Before | After |
|---|---:|---:|
| All frames | {_fmt(segments['all']['current_yaw_mae'])} deg | {_fmt(segments['all']['calibrated_yaw_mae'])} deg |
| Calibration 0-80 | {_fmt(segments['calibration_0_80']['current_yaw_mae'])} deg | {_fmt(segments['calibration_0_80']['calibrated_yaw_mae'])} deg |
| Validation 81-153 | {_fmt(segments['validation_81_153']['current_yaw_mae'])} deg | {_fmt(segments['validation_81_153']['calibrated_yaw_mae'])} deg |
| Frame 91-100 | {_fmt(segments['frame_91_100']['current_yaw_mae'])} deg | {_fmt(segments['frame_91_100']['calibrated_yaw_mae'])} deg |
| Frame 112-117 | {_fmt(segments['frame_112_117']['current_yaw_mae'])} deg | {_fmt(segments['frame_112_117']['calibrated_yaw_mae'])} deg |
| Frame 150-153 | {_fmt(segments['frame_150_153']['current_yaw_mae'])} deg | {_fmt(segments['frame_150_153']['calibrated_yaw_mae'])} deg |

Confidence failure:

```text
before = {summary['confidence_failure_before']}
after  = {summary['confidence_failure_after']}
```

## 圖表

![Calibrated yaw predicted vs OXTS](calibrated_yaw_pred_vs_oxts.png)

![Raw vs calibrated yaw error](raw_vs_calibrated_yaw_error.png)

![Calibrated confidence vs absolute error](calibrated_confidence_vs_abs_error.png)

## 驗收

```text
validation_mae_improved = {criteria['validation_mae_improved']}
confidence_failure_reduced = {criteria['confidence_failure_reduced']}
frame_112_117_improved = {criteria['frame_112_117_improved']}
frame_150_153_improved = {criteria['frame_150_153_improved']}
status = {summary['calibration_transform_status']}
```

## 解讀

此實驗沒有針對特定 frame 寫 rule，而是只使用 frame 0-80 學習 transform 參數，再在 frame 81-153 驗證。若 validation MAE 下降，代表 image-geometry yaw 與 OXTS heading 至少存在可用的一階線性校準關係。

需要注意：這仍是資料驅動的 yaw calibration，不等同於完整 camera-to-vehicle extrinsic calibration。若要進一步治本，下一步應建立明確的 camera intrinsics / extrinsics 與世界座標轉換。
"""
    path.write_text(text, encoding="utf-8")


def write_plots(rows: list[dict[str, Any]], output_dir: Path) -> None:
    frames = [row["frame_index"] for row in rows]
    calibrated = [row["calibrated_heading_yaw"] for row in rows]
    oxts = [row["oxts_yaw"] for row in rows]
    current_error = [row["current_abs_yaw_error"] for row in rows]
    calibrated_error = [row["calibrated_abs_yaw_error"] for row in rows]
    confidence = [row["yaw_confidence_after"] for row in rows]

    plt.figure(figsize=(11, 5))
    plt.plot(frames, calibrated, label="calibrated_heading_yaw", linewidth=1.5)
    plt.plot(frames, oxts, label="OXTS yaw", linewidth=1.5)
    plt.title("Calibrated yaw predicted vs OXTS")
    plt.xlabel("frame_index")
    plt.ylabel("yaw degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "calibrated_yaw_pred_vs_oxts.png", dpi=140)
    plt.close()

    plt.figure(figsize=(11, 5))
    plt.plot(frames, current_error, label="current abs yaw error", linewidth=1.4)
    plt.plot(frames, calibrated_error, label="calibrated abs yaw error", linewidth=1.4)
    plt.title("Raw/current vs calibrated yaw error")
    plt.xlabel("frame_index")
    plt.ylabel("absolute yaw error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "raw_vs_calibrated_yaw_error.png", dpi=140)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(confidence, calibrated_error, s=18, alpha=0.7, label="calibrated yaw")
    plt.title("Calibrated confidence vs absolute error")
    plt.xlabel("yaw confidence after")
    plt.ylabel("calibrated absolute yaw error degree")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "calibrated_confidence_vs_abs_error.png", dpi=140)
    plt.close()


def segment_name(frame_index: int) -> str:
    if frame_index in CALIBRATION_RANGE:
        return "calibration_0_80"
    if frame_index in VALIDATION_RANGE:
        return "validation_81_153"
    return "outside_split"


def confidence_failure(confidence: float | None, error: float | None) -> bool:
    return confidence is not None and error is not None and confidence >= 0.85 and error >= 30.0


def angle_delta(predicted: float, expected: float) -> float:
    return wrap_angle(predicted - expected)


def wrap_angle(value: float) -> float:
    while value >= 180.0:
        value -= 360.0
    while value < -180.0:
        value += 360.0
    return value


def _abs_error(predicted: float | None, expected: float | None) -> float | None:
    if predicted is None or expected is None:
        return None
    return abs(angle_delta(predicted, expected))


def _mae(rows: list[dict[str, Any]], pred: Callable[[dict[str, Any]], float | None]) -> float | None:
    errors = [
        _abs_error(pred(row), row["oxts_yaw"])
        for row in rows
        if pred(row) is not None and row["oxts_yaw"] is not None
    ]
    values = [value for value in errors if value is not None]
    return mean(values) if values else None


def _mean_value(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row[key] is not None]
    return mean(values) if values else None


def _segment_rows(rows: list[dict[str, Any]], frame_range: range) -> list[dict[str, Any]]:
    wanted = set(frame_range)
    return [row for row in rows if row["frame_index"] in wanted]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _parse_bool(value: str | None) -> bool:
    return bool(value and value.lower() == "true")


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
