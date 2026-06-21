from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.optical_flow_pose_overlay_pipeline import (  # noqa: E402
    UncalibratedPoseOverlayConfig,
    UncalibratedPoseOverlayPipeline,
)
from src.contexts.motion_analysis.domain.flow_track import FlowVector  # noqa: E402
from src.contexts.motion_analysis.services.sparse_flow_tracker import SparseFlowTrackerConfig  # noqa: E402
from src.contexts.output.services.motion_debug_visualizer import draw_flow_vectors  # noqa: E402
from src.contexts.output.services.optical_flow_pose_visualizer import draw_uncalibrated_pose_overlay  # noqa: E402
from tools.evaluation.evaluate_uncalibrated_pose_overlay_against_oxts import run_evaluation  # noqa: E402


OUTLIER_FRAMES = [34, 35, 38, 73, 76, 77, 79, 80, 86, 97, 101, 103, 117, 118, 119]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run optical-flow pose baseline and outlier-frame deep dive.")
    parser.add_argument("--video", type=Path, default=Path("tools/output/kitti_no_overlay.mp4"))
    parser.add_argument("--oxts-dir", type=Path, default=Path("tools/input/oxts"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/optical_flow_pose/parameter_debug"))
    parser.add_argument("--debug-root", type=Path, default=Path("debug/experiments/optical_flow_pose"))
    parser.add_argument("--max-debug-frames", type=int, default=120)
    parser.add_argument("--output-debug-every-n-frames", type=int, default=10)
    parser.add_argument("--inspect-frames", type=int, nargs="*", default=OUTLIER_FRAMES)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_root = _resolve_in_project(args.output_root)
    debug_root = _resolve_in_project(args.debug_root)
    baseline_output = output_root / "baseline"
    baseline_debug = debug_root / "001_baseline"
    deep_dive_debug = debug_root / "005_outlier_frame_deep_dive"

    _prepare_dir(output_root, PROJECT_ROOT / "outputs")
    _prepare_dir(baseline_debug, PROJECT_ROOT / "debug")
    _prepare_dir(deep_dive_debug, PROJECT_ROOT / "debug")

    config = UncalibratedPoseOverlayConfig(
        sparse_flow=SparseFlowTrackerConfig(max_debug_frames=args.max_debug_frames),
        output_debug_every_n_frames=args.output_debug_every_n_frames,
    )
    result = UncalibratedPoseOverlayPipeline(config).run(args.video, baseline_output)
    evaluation = run_evaluation(
        Path(result.frame_pose_results_json),
        args.oxts_dir,
        baseline_output / "evaluation",
    )

    _write_baseline_debug(baseline_debug, args, result, evaluation.summary_json)
    comparison_rows = _read_csv(evaluation.comparison_csv)
    _write_deep_dive(deep_dive_debug, args.video, result, comparison_rows, args.inspect_frames)
    _write_parameter_debug_report(output_root / "evaluation_report.md", result, evaluation.summary_json, args.inspect_frames)

    print(f"Wrote baseline outputs: {baseline_output}")
    print(f"Wrote baseline debug: {baseline_debug}")
    print(f"Wrote outlier deep dive: {deep_dive_debug}")
    print(f"Wrote parameter debug report: {output_root / 'evaluation_report.md'}")
    return 0


def _resolve_in_project(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _prepare_dir(path: Path, allowed_root: Path) -> None:
    resolved = path.resolve()
    allowed = allowed_root.resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError(f"Refusing to clear directory outside {allowed}: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def _write_baseline_debug(
    baseline_debug: Path,
    args: argparse.Namespace,
    result: Any,
    summary_json: Path,
) -> None:
    (baseline_debug / "params").mkdir(parents=True, exist_ok=True)
    (baseline_debug / "metrics").mkdir(parents=True, exist_ok=True)
    (baseline_debug / "reports").mkdir(parents=True, exist_ok=True)
    config = {
        "video": str(args.video),
        "oxts_dir": str(args.oxts_dir),
        "output_root": str(args.output_root),
        "debug_root": str(args.debug_root),
        "max_debug_frames": args.max_debug_frames,
        "output_debug_every_n_frames": args.output_debug_every_n_frames,
        "warnings": result.intrinsics.warnings,
    }
    (baseline_debug / "params" / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    shutil.copy2(summary_json, baseline_debug / "metrics" / "relative_pose_vs_oxts_summary.json")
    report = [
        "# 001 Baseline",
        "",
        "此 baseline 保存目前 uncalibrated optical-flow pose overlay 的輸出，並以 OXTS frame-to-frame delta 做相對旋轉比較。",
        "",
        f"- Pose rows: {len(result.pose_rows)}",
        f"- Output video: {result.output_video}",
        f"- Pose JSON: {result.frame_pose_results_json}",
        "",
        "注意：目前仍使用 approximate K，因此這不是 calibrated pose result。",
    ]
    (baseline_debug / "reports" / "baseline_report.md").write_text("\n".join(report), encoding="utf-8")


def _write_deep_dive(
    deep_dive_debug: Path,
    video_path: Path,
    result: Any,
    comparison_rows: list[dict[str, str]],
    inspect_frames: list[int],
) -> None:
    params_dir = deep_dive_debug / "params"
    metrics_dir = deep_dive_debug / "metrics"
    frames_dir = deep_dive_debug / "frames"
    reports_dir = deep_dive_debug / "reports"
    for path in (params_dir, metrics_dir, frames_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)

    (params_dir / "config.json").write_text(
        json.dumps({"inspect_frames": inspect_frames, "video": str(video_path)}, indent=2),
        encoding="utf-8",
    )

    frames_by_index = _load_selected_video_frames(video_path, inspect_frames)
    vectors_by_frame: dict[int, list[FlowVector]] = {}
    for vector in result.sparse_flow.flow_vectors:
        vectors_by_frame.setdefault(vector.frame_index, []).append(vector)
    pose_by_frame = {row.frame_index: row for row in result.pose_rows}
    comparison_by_frame = {int(row["frame_index"]): row for row in comparison_rows}

    per_frame = []
    for frame_index in inspect_frames:
        frame = frames_by_index.get(frame_index)
        pose = pose_by_frame.get(frame_index)
        vectors = vectors_by_frame.get(frame_index, [])
        comparison = comparison_by_frame.get(frame_index, {})
        if frame is not None:
            cv2.imwrite(str(frames_dir / f"frame_{frame_index:06d}_input.png"), frame)
            cv2.imwrite(str(frames_dir / f"frame_{frame_index:06d}_flow_vectors.png"), draw_flow_vectors(frame, vectors))
            if pose is not None:
                overlay = draw_uncalibrated_pose_overlay(frame, vectors, pose)
                cv2.imwrite(str(frames_dir / f"frame_{frame_index:06d}_inliers_outliers.png"), overlay)
                cv2.imwrite(str(frames_dir / f"frame_{frame_index:06d}_pose_overlay.png"), overlay)

        payload = _frame_payload(frame_index, pose, vectors, comparison)
        per_frame.append(payload)
        (metrics_dir / f"frame_{frame_index:06d}.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    (metrics_dir / "outlier_frames.json").write_text(json.dumps(per_frame, indent=2), encoding="utf-8")
    (reports_dir / "experiment_report.md").write_text(_render_deep_dive_report(per_frame), encoding="utf-8")


def _frame_payload(
    frame_index: int,
    pose: Any,
    vectors: list[FlowVector],
    comparison: dict[str, str],
) -> dict[str, Any]:
    return {
        "frame_index": frame_index,
        "tracked_point_count": pose.tracked_point_count if pose is not None else 0,
        "valid_track_count": len(vectors),
        "inlier_count": pose.inlier_count if pose is not None else 0,
        "inlier_ratio": pose.inlier_ratio if pose is not None else 0.0,
        "yaw_deg": pose.yaw_deg if pose is not None else None,
        "pitch_deg": pose.pitch_deg if pose is not None else None,
        "roll_deg": pose.roll_deg if pose is not None else None,
        "oxts_delta_yaw": _float_or_none(comparison.get("oxts_relative_yaw")),
        "oxts_delta_pitch": _float_or_none(comparison.get("oxts_relative_pitch")),
        "oxts_delta_roll": _float_or_none(comparison.get("oxts_relative_roll")),
        "abs_yaw_error": _float_or_none(comparison.get("abs_yaw_error")),
        "abs_pitch_error": _float_or_none(comparison.get("abs_pitch_error")),
        "abs_roll_error": _float_or_none(comparison.get("abs_roll_error")),
        "confidence": pose.confidence if pose is not None else 0.0,
        "warnings": pose.warnings if pose is not None else ["missing_pose_row"],
    }


def _render_deep_dive_report(rows: list[dict[str, Any]]) -> str:
    sorted_pitch = sorted(rows, key=lambda row: row.get("abs_pitch_error") or -1, reverse=True)[:5]
    sorted_roll = sorted(rows, key=lambda row: row.get("abs_roll_error") or -1, reverse=True)[:5]
    lines = [
        "# 005 Outlier Frame Deep Dive",
        "",
        "本報告針對 optical-flow pose prototype 的 outlier frames 做逐幀檢查。",
        "",
        "## Pitch Worst",
        "",
    ]
    for row in sorted_pitch:
        lines.append(
            f"- frame {row['frame_index']}: abs_pitch_error={_fmt(row['abs_pitch_error'])}, "
            f"inlier_ratio={_fmt(row['inlier_ratio'])}, valid_tracks={row['valid_track_count']}"
        )
    lines.extend(["", "## Roll Worst", ""])
    for row in sorted_roll:
        lines.append(
            f"- frame {row['frame_index']}: abs_roll_error={_fmt(row['abs_roll_error'])}, "
            f"inlier_ratio={_fmt(row['inlier_ratio'])}, valid_tracks={row['valid_track_count']}"
        )
    lines.extend(
        [
            "",
            "## 後續判讀方式",
            "",
            "- 如果 inlier ratio 偏高但角度錯誤，優先檢查 approximate K sensitivity 或 recoverPose ambiguity。",
            "- 如果 valid tracks 偏少，優先檢查 Shi-Tomasi / LK tracking 參數。",
            "- 如果 inlier ratio 偏低，優先檢查 RANSAC threshold 或特徵點空間分布。",
        ]
    )
    return "\n".join(lines)


def _write_parameter_debug_report(
    report_path: Path,
    result: Any,
    summary_json: Path,
    inspect_frames: list[int],
) -> None:
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    pitch_worst = summary["top_10_pitch_error_frames"][0]
    roll_worst = summary["top_10_roll_error_frames"][0]
    yaw_worst = summary["top_10_yaw_error_frames"][0]
    lines = [
        "# Optical-Flow Pose 參數 Debug 評估報告",
        "",
        "本次依照 `optical_flow_parameter_debug_prompt.md` 先完成第一輪：baseline snapshot + outlier frame deep dive。",
        "此輪尚未做大範圍參數 sweep，目的是先確認 outlier 的型態，避免盲目調參。",
        "",
        "## 實驗 ID",
        "",
        "- `001_baseline`: 保存目前 baseline metrics、overlay、pose JSON 與 OXTS relative evaluation。",
        "- `005_outlier_frame_deep_dive`: 針對 priority outlier frames 輸出 input frame、flow vectors、RANSAC inlier/outlier overlay 與 per-frame JSON。",
        "",
        "## Baseline Metrics",
        "",
        f"- Rows compared: {summary['total_rows']}",
        f"- Mean inlier ratio: {_fmt(summary['mean_inlier_ratio'])}",
        f"- Mean confidence: {_fmt(summary['mean_confidence'])}",
        f"- Mean abs yaw error: {_fmt(summary['mean_abs_yaw_error'])} deg",
        f"- Mean abs pitch error: {_fmt(summary['mean_abs_pitch_error'])} deg",
        f"- Mean abs roll error: {_fmt(summary['mean_abs_roll_error'])} deg",
        f"- Max abs pitch error: {_fmt(summary['max_abs_pitch_error'])} deg",
        f"- Max abs roll error: {_fmt(summary['max_abs_roll_error'])} deg",
        "",
        "## Outlier 分析",
        "",
        (
            f"- Pitch 最大錯誤在 frame {pitch_worst['frame_index']}："
            f"abs_pitch_error={_fmt(pitch_worst['abs_error'])} deg，"
            f"inlier_ratio={_fmt(pitch_worst['inlier_ratio'])}。"
        ),
        (
            f"- Roll 最大錯誤在 frame {roll_worst['frame_index']}："
            f"abs_roll_error={_fmt(roll_worst['abs_error'])} deg，"
            f"inlier_ratio={_fmt(roll_worst['inlier_ratio'])}。"
        ),
        (
            f"- Yaw 最大錯誤在 frame {yaw_worst['frame_index']}："
            f"abs_yaw_error={_fmt(yaw_worst['abs_error'])} deg，"
            f"inlier_ratio={_fmt(yaw_worst['inlier_ratio'])}。"
        ),
        "- Pitch outlier 多數發生在高 inlier ratio frame，代表問題不只是 LK tracking 掉點，較可能與 approximate K、recoverPose ambiguity 或場景幾何退化有關。",
        "- Roll outlier 集中在 frame 117-119，valid tracks 只有約 60，但 inlier ratio 很高；這類 frame 要同時檢查特徵數量、空間分布與 Essential Matrix 解的穩定性。",
        "- Frame 97/101 類型的 yaw outlier confidence 已偏低，confidence 對低 inlier ratio frame 有一定辨識力；但 frame 79/34/117 這類高 inlier 高錯誤仍需新增 outlier penalty。",
        "",
        "## Outputs",
        "",
        f"- Overlay video: {result.output_video}",
        f"- Pose JSON: {result.frame_pose_results_json}",
        "- Evaluation: outputs/optical_flow_pose/parameter_debug/baseline/evaluation/",
        "- Debug deep dive: debug/experiments/optical_flow_pose/005_outlier_frame_deep_dive/",
        "",
        "## Inspected Frames",
        "",
        ", ".join(str(frame) for frame in inspect_frames),
        "",
        "## Decision",
        "",
        "目前尚未接受任何新參數。根據本輪 deep dive，下一輪建議先做 `004_approx_k_sensitivity` 與 `003_ransac_threshold_sweep`，再補 `006_confidence_calibration`。LK/feature sweep 可保留，但不建議作為第一優先，因為最大 pitch outlier 的 valid tracks 並不低。",
        "",
        "## Required Warning",
        "",
        "目前結果仍是 approximate K debug prototype，不是 calibrated pose result。",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _load_selected_video_frames(video_path: Path, frame_indices: list[int]) -> dict[int, Any]:
    wanted = set(frame_indices)
    frames = {}
    capture = cv2.VideoCapture(str(video_path))
    try:
        frame_index = 0
        while capture.isOpened() and len(frames) < len(wanted):
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index in wanted:
                frames[frame_index] = frame.copy()
            frame_index += 1
    finally:
        capture.release()
    return frames


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
