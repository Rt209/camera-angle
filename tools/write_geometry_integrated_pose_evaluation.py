from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any


INTEGRATED_COLUMNS = [
    "frame_index",
    "time_sec",
    "segment",
    "pred_yaw_current",
    "pred_yaw_calibrated",
    "oxts_yaw",
    "yaw_error_current",
    "yaw_error_calibrated",
    "abs_yaw_error_current",
    "abs_yaw_error_calibrated",
    "pred_pitch",
    "oxts_pitch",
    "pitch_error",
    "abs_pitch_error",
    "pred_roll",
    "oxts_roll",
    "roll_error",
    "abs_roll_error",
    "confidence",
    "yaw_confidence_before",
    "yaw_confidence_after",
    "pitch_confidence",
    "roll_confidence",
    "confidence_failure_before",
    "confidence_failure_after",
    "status",
    "detected_line_count",
    "perspective_line_count",
    "vanishing_point_candidate_count",
    "horizon_candidate_count",
    "yaw_calibration_model",
    "yaw_calibration_scale",
    "yaw_calibration_offset",
    "vp_temporal_jump",
    "vp_side_flip",
    "vp_cluster_ambiguity",
    "line_support_consistency",
    "yaw_warning_flags",
]


SEGMENTS = {
    "all": range(0, 154),
    "calibration_0_80": range(0, 81),
    "validation_81_153": range(81, 154),
    "frame_91_100": range(91, 101),
    "frame_112_117": range(112, 118),
    "frame_150_153": range(150, 154),
}


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = build_integrated_rows(args.video_pose_csv, args.calibrated_yaw_csv)
    summary = build_summary(rows)

    integrated_csv = args.output_dir / "integrated_pose_vs_oxts.csv"
    summary_json = args.output_dir / "integrated_pose_summary.json"
    report_md = args.output_dir / "integrated_pose_report.md"

    write_csv(integrated_csv, rows, INTEGRATED_COLUMNS)
    write_json(summary_json, summary)
    write_report(report_md, summary)

    print(f"Wrote integrated CSV: {integrated_csv}")
    print(f"Wrote integrated summary: {summary_json}")
    print(f"Wrote integrated report: {report_md}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write integrated pitch/yaw/roll geometry pose evaluation.")
    parser.add_argument("--video-pose-csv", type=Path, default=Path("outputs/video_pose/evaluation/pose_vs_oxts.csv"))
    parser.add_argument(
        "--calibrated-yaw-csv",
        type=Path,
        default=Path("outputs/geometry_yaw_oxts_experiment/evaluation/calibrated_pose_vs_oxts.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/geometry_yaw_oxts_experiment/evaluation"))
    return parser


def build_integrated_rows(video_pose_csv: Path, calibrated_yaw_csv: Path) -> list[dict[str, Any]]:
    calibrated_by_frame = {
        int(row["frame_index"]): row
        for row in csv.DictReader(calibrated_yaw_csv.open(newline="", encoding="utf-8"))
    }
    rows: list[dict[str, Any]] = []
    for current in csv.DictReader(video_pose_csv.open(newline="", encoding="utf-8")):
        frame_index = int(current["frame_index"])
        calibrated = calibrated_by_frame[frame_index]
        pred_yaw_current = _float(current.get("pred_yaw"))
        pred_yaw_calibrated = _float(calibrated.get("calibrated_heading_yaw"))
        oxts_yaw = _float(current.get("oxts_yaw"))
        rows.append(
            {
                "frame_index": frame_index,
                "time_sec": _float(current.get("time_sec")),
                "segment": calibrated.get("segment") or segment_name(frame_index),
                "pred_yaw_current": pred_yaw_current,
                "pred_yaw_calibrated": pred_yaw_calibrated,
                "oxts_yaw": oxts_yaw,
                "yaw_error_current": _angle_delta(pred_yaw_current, oxts_yaw),
                "yaw_error_calibrated": _angle_delta(pred_yaw_calibrated, oxts_yaw),
                "abs_yaw_error_current": _abs_angle_error(pred_yaw_current, oxts_yaw),
                "abs_yaw_error_calibrated": _abs_angle_error(pred_yaw_calibrated, oxts_yaw),
                "pred_pitch": _float(current.get("pred_pitch")),
                "oxts_pitch": _float(current.get("oxts_pitch")),
                "pitch_error": _float(current.get("pitch_error")),
                "abs_pitch_error": _float(current.get("abs_pitch_error")),
                "pred_roll": _float(current.get("pred_roll")),
                "oxts_roll": _float(current.get("oxts_roll")),
                "roll_error": _float(current.get("roll_error")),
                "abs_roll_error": _float(current.get("abs_roll_error")),
                "confidence": _float(current.get("confidence")),
                "yaw_confidence_before": _float(calibrated.get("yaw_confidence_before")),
                "yaw_confidence_after": _float(calibrated.get("yaw_confidence_after")),
                "pitch_confidence": _float(current.get("pitch_confidence")),
                "roll_confidence": _float(current.get("roll_confidence")),
                "confidence_failure_before": _parse_bool(calibrated.get("confidence_failure_before")),
                "confidence_failure_after": _parse_bool(calibrated.get("confidence_failure_after")),
                "status": current.get("status"),
                "detected_line_count": _int(current.get("detected_line_count")),
                "perspective_line_count": _int(current.get("perspective_line_count")),
                "vanishing_point_candidate_count": _int(current.get("vanishing_point_candidate_count")),
                "horizon_candidate_count": _int(current.get("horizon_candidate_count")),
                "yaw_calibration_model": calibrated.get("yaw_calibration_model"),
                "yaw_calibration_scale": _float(calibrated.get("yaw_calibration_scale")),
                "yaw_calibration_offset": _float(calibrated.get("yaw_calibration_offset")),
                "vp_temporal_jump": _float(calibrated.get("vp_temporal_jump")),
                "vp_side_flip": _parse_bool(calibrated.get("vp_side_flip")),
                "vp_cluster_ambiguity": _float(calibrated.get("vp_cluster_ambiguity")),
                "line_support_consistency": _float(calibrated.get("line_support_consistency")),
                "yaw_warning_flags": calibrated.get("yaw_warning_flags"),
            }
        )
    return rows


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total_rows": len(rows),
        "overall": segment_summary(rows),
        "segments": {},
        "worst_frames": {
            "yaw_current": worst_frames(rows, "abs_yaw_error_current", "pred_yaw_current", "oxts_yaw"),
            "yaw_calibrated": worst_frames(rows, "abs_yaw_error_calibrated", "pred_yaw_calibrated", "oxts_yaw"),
            "pitch": worst_frames(rows, "abs_pitch_error", "pred_pitch", "oxts_pitch"),
            "roll": worst_frames(rows, "abs_roll_error", "pred_roll", "oxts_roll"),
        },
        "confidence_failure_before": sum(row["confidence_failure_before"] for row in rows),
        "confidence_failure_after": sum(row["confidence_failure_after"] for row in rows),
    }
    for name, frame_range in SEGMENTS.items():
        segment_rows = [row for row in rows if row["frame_index"] in set(frame_range)]
        summary["segments"][name] = segment_summary(segment_rows)
    return summary


def segment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "yaw_current_mae": _mean_key(rows, "abs_yaw_error_current"),
        "yaw_calibrated_mae": _mean_key(rows, "abs_yaw_error_calibrated"),
        "yaw_current_rmse": _rmse_key(rows, "yaw_error_current"),
        "yaw_calibrated_rmse": _rmse_key(rows, "yaw_error_calibrated"),
        "pitch_mae": _mean_key(rows, "abs_pitch_error"),
        "pitch_rmse": _rmse_key(rows, "pitch_error"),
        "roll_mae": _mean_key(rows, "abs_roll_error"),
        "roll_rmse": _rmse_key(rows, "roll_error"),
        "confidence_failure_before": sum(row["confidence_failure_before"] for row in rows),
        "confidence_failure_after": sum(row["confidence_failure_after"] for row in rows),
    }


def worst_frames(rows: list[dict[str, Any]], error_key: str, pred_key: str, expected_key: str, limit: int = 10) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        (row for row in rows if row[error_key] is not None),
        key=lambda row: row[error_key],
        reverse=True,
    )
    return [
        {
            "rank": index,
            "frame_index": row["frame_index"],
            "time_sec": row["time_sec"],
            "pred_value": row[pred_key],
            "oxts_value": row[expected_key],
            "abs_error": row[error_key],
            "confidence": row["confidence"],
            "status": row["status"],
        }
        for index, row in enumerate(sorted_rows[:limit], start=1)
    ]


def write_report(path: Path, summary: dict[str, Any]) -> None:
    overall = summary["overall"]
    segments = summary["segments"]
    text = f"""# Integrated Geometry Pose Evaluation

本報告把 geometry yaw calibration 實驗的 yaw、pitch、roll 數據整合在同一份 evaluation 中。

## 資料來源

```text
Current pitch / roll / reliability-gated yaw:
outputs/video_pose/evaluation/pose_vs_oxts.csv

Calibrated yaw:
outputs/geometry_yaw_oxts_experiment/evaluation/calibrated_pose_vs_oxts.csv

Integrated output:
outputs/geometry_yaw_oxts_experiment/evaluation/integrated_pose_vs_oxts.csv
```

## 整體指標

| Metric | Value |
|---|---:|
| Rows | {summary['total_rows']} |
| Yaw MAE current | {_fmt(overall['yaw_current_mae'])} deg |
| Yaw MAE calibrated | {_fmt(overall['yaw_calibrated_mae'])} deg |
| Pitch MAE | {_fmt(overall['pitch_mae'])} deg |
| Roll MAE | {_fmt(overall['roll_mae'])} deg |
| Yaw RMSE current | {_fmt(overall['yaw_current_rmse'])} deg |
| Yaw RMSE calibrated | {_fmt(overall['yaw_calibrated_rmse'])} deg |
| Pitch RMSE | {_fmt(overall['pitch_rmse'])} deg |
| Roll RMSE | {_fmt(overall['roll_rmse'])} deg |
| Confidence failure before | {summary['confidence_failure_before']} |
| Confidence failure after | {summary['confidence_failure_after']} |

## Segment 指標

| Segment | Yaw Current MAE | Yaw Calibrated MAE | Pitch MAE | Roll MAE | Failure Before | Failure After |
|---|---:|---:|---:|---:|---:|---:|
| Calibration 0-80 | {_fmt(segments['calibration_0_80']['yaw_current_mae'])} | {_fmt(segments['calibration_0_80']['yaw_calibrated_mae'])} | {_fmt(segments['calibration_0_80']['pitch_mae'])} | {_fmt(segments['calibration_0_80']['roll_mae'])} | {segments['calibration_0_80']['confidence_failure_before']} | {segments['calibration_0_80']['confidence_failure_after']} |
| Validation 81-153 | {_fmt(segments['validation_81_153']['yaw_current_mae'])} | {_fmt(segments['validation_81_153']['yaw_calibrated_mae'])} | {_fmt(segments['validation_81_153']['pitch_mae'])} | {_fmt(segments['validation_81_153']['roll_mae'])} | {segments['validation_81_153']['confidence_failure_before']} | {segments['validation_81_153']['confidence_failure_after']} |
| Frame 91-100 | {_fmt(segments['frame_91_100']['yaw_current_mae'])} | {_fmt(segments['frame_91_100']['yaw_calibrated_mae'])} | {_fmt(segments['frame_91_100']['pitch_mae'])} | {_fmt(segments['frame_91_100']['roll_mae'])} | {segments['frame_91_100']['confidence_failure_before']} | {segments['frame_91_100']['confidence_failure_after']} |
| Frame 112-117 | {_fmt(segments['frame_112_117']['yaw_current_mae'])} | {_fmt(segments['frame_112_117']['yaw_calibrated_mae'])} | {_fmt(segments['frame_112_117']['pitch_mae'])} | {_fmt(segments['frame_112_117']['roll_mae'])} | {segments['frame_112_117']['confidence_failure_before']} | {segments['frame_112_117']['confidence_failure_after']} |
| Frame 150-153 | {_fmt(segments['frame_150_153']['yaw_current_mae'])} | {_fmt(segments['frame_150_153']['yaw_calibrated_mae'])} | {_fmt(segments['frame_150_153']['pitch_mae'])} | {_fmt(segments['frame_150_153']['roll_mae'])} | {segments['frame_150_153']['confidence_failure_before']} | {segments['frame_150_153']['confidence_failure_after']} |

## Worst Frames

### Calibrated Yaw

{_format_worst(summary['worst_frames']['yaw_calibrated'])}

### Pitch

{_format_worst(summary['worst_frames']['pitch'])}

### Roll

{_format_worst(summary['worst_frames']['roll'])}

## 解讀

- Calibrated yaw MAE 比 current yaw MAE 低，代表 calibration transform 對 yaw 有整體改善。
- Pitch 與 roll 沒有套用 calibration transform，這裡保留原本 geometry pipeline 的數據，用來確認 yaw calibration 沒有混淆其他角度。
- Confidence failure 從 before 到 after 的變化，可用來檢查高 confidence 但高 yaw error 的問題是否下降。
- Frame 91-100 是 reliability gate 已改善的區段；frame 112-117 與 150-153 是 calibration transform 主要改善的區段。
"""
    path.write_text(text, encoding="utf-8")


def segment_name(frame_index: int) -> str:
    if frame_index <= 80:
        return "calibration_0_80"
    return "validation_81_153"


def _angle_delta(predicted: float | None, expected: float | None) -> float | None:
    if predicted is None or expected is None:
        return None
    delta = predicted - expected
    while delta >= 180.0:
        delta -= 360.0
    while delta < -180.0:
        delta += 360.0
    return delta


def _abs_angle_error(predicted: float | None, expected: float | None) -> float | None:
    delta = _angle_delta(predicted, expected)
    return abs(delta) if delta is not None else None


def _mean_key(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row[key] is not None]
    return mean(values) if values else None


def _rmse_key(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row[key] is not None]
    if not values:
        return None
    return math.sqrt(sum(value * value for value in values) / len(values))


def _format_worst(rows: list[dict[str, Any]]) -> str:
    lines = ["```text"]
    for row in rows[:5]:
        lines.append(
            f"frame {row['frame_index']}: pred={row['pred_value']:.4f}, "
            f"oxts={row['oxts_value']:.4f}, abs_error={row['abs_error']:.4f}, "
            f"confidence={row['confidence']:.2f}"
        )
    lines.append("```")
    return "\n".join(lines)


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


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _parse_bool(value: str | None) -> bool:
    return bool(value and value.lower() == "true")


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
