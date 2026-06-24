# Geometry Based Pose Implementation Plan

## Evaluation Metrics Implementation

實作位置：`tools/evaluation/evaluate_video_pose_against_oxts.py`。

| Function | Responsibility |
|---|---|
| `compute_precision_at_theta()` | 正確有效姿態數除以有效姿態數 |
| `compute_recall_at_theta()` | 正確有效姿態數除以全部 reference samples |
| `compute_geodesic_mae()` | 有效 Geodesic Error 的平均值 |
| `compute_p95_error()` | 計算 Geodesic Error 第 95 百分位 |
| `compute_jitter()` | 影片連續 rotation-error change 的 RMS |

```bash
python tools/evaluation/evaluate_video_pose_against_oxts.py \
  --pose-csv outputs/video_pose/pose_timeline.csv \
  --oxts-dir data/samples/kitti/references/oxts \

  --theta-deg 3.0
```

需要診斷檔時加入 `--save-plots --save-worst-frames`。評估器優先使用 `comparison_ready=true` 的 `calibrated_heading_yaw`；否則沿用 image geometry yaw 並標記為 diagnostic-only。

## 1. 目的

本文件根據 `02_Analysis/README.md` 與 `03_Design/README.md`，規劃 Geometry Based Pose 第一版實作。Implementation 階段的重點是把 D1 到 D10 設計模組落成可執行階段。

## 2. Implementation / Design 對應表

| Phase | 對應 Design | 實作重點 | 主要工具 |
|---|---|---|---|
| P1 | D1 Input | 讀取圖片、驗證格式、建立 frame packet | OpenCV / Pillow |
| P2 | D2 Preprocessing | gray、resize、blur、Canny | OpenCV |
| P3 | D3 Line Feature | HoughLinesP、line filtering、orientation classification | OpenCV / NumPy |
| P4 | D4 Roll | orientation histogram / weighted median | NumPy |
| P5 | D5 Pitch | horizon selection、pitch formula | NumPy |
| P6 | D6 Yaw | VP candidates、voting、yaw formula | NumPy |
| P7 | D7-D8 Pose / Confidence | PoseResult、per-angle confidence | JSON / NumPy |
| P8 | D9 Output | JSON、Rich Table、debug artifacts | Rich / OpenCV drawing |
| P9 | D10 Verification | metrics、failure cases、synthetic tests | pytest / CSV / Markdown |

## 3. 實作資料流

```mermaid
flowchart TD
    A[Input Image] -->|image_path| P1[P1 Image Input]
    P1 -->|frame_packet + bgr_frame| P2[P2 Preprocessing]
    P2 -->|edge_map + gray_frame| P3[P3 Line Detection]
    P3 -->|LineSegment[] + orientation classes| P4[P4 Roll]
    P3 -->|horizontal candidates| P5[P5 Pitch]
    P3 -->|perspective lines| P6[P6 Yaw]
    P4 -->|roll_result| P7[P7 Pose / Confidence]
    P5 -->|pitch_result| P7
    P6 -->|yaw_result| P7
    P7 -->|pose_result_with_confidence| P8[P8 Output]
    P1 -->|bgr_frame| P8
    P2 -->|debug frames| P8
    P3 -->|line debug data| P8
    P8 -->|pose_result.json + debug_artifacts| P9[P9 Verification]
```

## 4. Stage 分組

| Stage | 覆蓋 Phase | 主要成果 |
|---|---|---|
| Stage 0-3 | P1-P4 | foundation、preprocessing、line detection、roll |
| Stage 4-7 | P5-P8 | pitch、yaw、PoseResult、confidence、debug output |
| Stage 8-10 | P9 + extensions | validation、video extension、realtime extension |

## 5. Output Artifacts

```text
debug/01_input.png
debug/02_grayscale.png
debug/03_blurred.png
debug/04_edges.png
debug/05_detected_lines.png
debug/06_filtered_lines.png
debug/07_line_orientation_debug.png
debug/08_roll_candidate_lines.png
debug/09_roll_orientation_histogram.png
debug/10_roll_overlay.png
debug/11_horizon_candidates.png
debug/12_selected_horizon.png
debug/13_pitch_overlay.png
debug/14_perspective_lines.png
debug/15_vanishing_point_candidates.png
debug/16_selected_vanishing_point.png
debug/17_yaw_overlay.png
debug/18_pose_overlay.png
pose_result.json
metrics_report.md
```

## 6. 建議 Config

```yaml
input:
  supported_extensions: [jpg, jpeg, png]

preprocessing:
  resize_width: 960
  gaussian_kernel: [5, 5]
  canny_threshold1: 50
  canny_threshold2: 150

lines:
  min_line_length: 40
  max_line_gap: 10
  horizontal_threshold_deg: 8.0
  vertical_threshold_deg: 12.0

camera_model:
  mode: focal_fallback
  focal_reference: min_image_dimension

pose:
  angle_unit: degree
  allow_partial_result: true

debug:
  enabled: true
  output_dir: debug/
```

## 7. CLI 草案

```bash
python main.py --path examples/0.png
python main.py --path examples/0.png --json
python main.py --path examples/0.png --debug-dir debug/examples_0
```

## 8. 實作順序建議

1. 完成 Stage 0-3，先讓 roll baseline 穩定。
2. 完成 Stage 4-7，加入 pitch、yaw、PoseResult 與 debug artifacts。
3. 完成 Stage 8 validation，建立 metrics report。
4. 視需求擴充 Stage 9 video 與 Stage 10 realtime。

## 9. 延伸文件

```text
04_Implementation/stage_0_3_foundation_and_roll.md
04_Implementation/stage_4_7_pose_integration_and_debug.md
04_Implementation/stage_8_10_validation_video_realtime.md
```
# Evaluation core migration

Geometry reference-based evaluation now runs through `src/app/evaluation/geometry_service.py`. Prediction reading, OXTS loading, source-frame alignment, ZYX/geodesic math, metrics, and artifact services are owned by `src/contexts/evaluation`. Raw Geometry yaw remains diagnostic-only unless calibrated; the migration does not change its formulas or pose semantics.
