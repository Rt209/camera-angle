# Geometry Based Pose Design

## Evaluation Module Design

| Logical module | Responsibility | Output |
|---|---|---|
| `PoseErrorCalculator` | 將 predicted／reference YPR 轉成 ZYX rotation matrix並計算 SO(3) error | `geodesic_error_deg` |
| `MetricEvaluator` | 計算 Precision、Recall、Geodesic MAE 與 P95 | `selected_metrics` |
| `JitterAnalyzer` | geometry video 依連續 frame index 計算 rotation-error change RMS | `jitter_deg` |
| `PoseSemanticsGuard` | 選用 calibrated heading，否則標記 raw image geometry yaw 為 diagnostic | `comparison_ready`, warnings |
| `ResultLogger` | 寫入精簡 artifacts，依旗標產生 plots／worst frames | CSV、JSON、Markdown |

為保留既有 yaw debug／calibration 工具相容性，Geometry eval 使用：

```text
evaluation/
  per_frame.csv
  summary.json
  evaluation_report.md
```

`--save-plots` 與 `--save-worst-frames` 才產生額外診斷檔案。

## 1. 目的

本文件根據 `02_Analysis/README.md` 的 A1 到 A10 架構，整理 Geometry Based Pose 的設計入口。Design 階段的重點是把 Analysis 的模組、資料交換方式、可用技術與小階段流程轉成可實作的 D1 到 D10 設計模組。

第一版設計主線：

```text
Input Image
+ preprocessing
+ Canny edge detection
+ HoughLinesP line detection
+ orientation / roll estimation
+ horizon / pitch estimation
+ vanishing point / yaw estimation
+ PoseResult + confidence
+ JSON / Rich Table / debug artifacts
```

## 2. Analysis / Design 對應表

| Analysis ID | Analysis 架構 | Design ID | Design 模組 | 主要責任 |
|---|---|---|---|---|
| A1 | Image Input Analysis | D1 | Input Context | 讀取圖片、驗證格式、建立 `FramePacket` |
| A2 | Preprocessing Analysis | D2 | Preprocessing Context | 產生 gray、blurred、edge map |
| A3 | Line Detection Analysis | D3 | Line Feature Context | 偵測與分類 `LineSegment[]` |
| A4 | Orientation / Roll Analysis | D4 | Roll Estimator | 由線段方向估計 roll |
| A5 | Horizon / Pitch Analysis | D5 | Pitch Estimator | 由 horizon 與 camera model 估計 pitch |
| A6 | Vanishing Point / Yaw Analysis | D6 | Yaw Estimator | 由 vanishing point 估計 yaw |
| A7 | Pose Integration Analysis | D7 | Pose Integrator | 整合 yaw / pitch / roll 成 `PoseResult` |
| A8 | Confidence Analysis | D8 | Confidence Scorer | 計算 per-angle 與 overall confidence |
| A9 | Debug / Output Analysis | D9 | Output Context | 產生 JSON、Rich Table、debug artifacts |
| A10 | Verification Analysis | D10 | Evaluation Context | 計算 metrics、failure cases 與 report |

## 3. 模組溝通與資料交換設計

```mermaid
flowchart TD
    D1[D1 Input Context] -->|frame_packet: json<br/>bgr_frame: ndarray| D2[D2 Preprocessing]
    D2 -->|preprocess_result: json<br/>gray_frame: ndarray<br/>edge_map: ndarray| D3[D3 Line Feature Context]
    D3 -->|line_result: json<br/>LineSegment[]| D4[D4 Roll Estimator]
    D3 -->|line_result: json<br/>horizontal candidates| D5[D5 Pitch Estimator]
    D3 -->|perspective_lines: LineSegment[]| D6[D6 Yaw Estimator]
    D4 -->|roll_result: json| D7[D7 Pose Integrator]
    D5 -->|pitch_result: json| D7
    D6 -->|yaw_result: json| D7
    D7 -->|pose_result: json| D8[D8 Confidence Scorer]
    D8 -->|pose_result_with_confidence: json| D9[D9 Output Context]
    D1 -->|bgr_frame: ndarray| D9
    D2 -->|debug frames: ndarray| D9
    D3 -->|debug lines: json| D9
    D9 -->|pose_result.json<br/>debug_artifacts: png| D10[D10 Evaluation Context]
    D10 -->|metrics_report.json<br/>failure_cases.md| OUT[Output Artifacts]
```

## 4. 建議模組結構

```text
src/app/cli.py
src/app/pipeline.py
src/contexts/input/
src/contexts/preprocessing/
src/contexts/geometry_features/
src/contexts/pose_estimation/
src/contexts/output/
src/contexts/evaluation/
src/shared/
```

## 5. 模組輸入與輸出

| Design ID | 模組 | 輸入 | 輸出 |
|---|---|---|---|
| D1 | Image Reader | `image_path` | `frame_packet`, `bgr_frame` |
| D2 | Preprocessor | `bgr_frame`, preprocess config | `gray_frame`, `edge_map`, `scale_meta` |
| D3 | Line Detector | `edge_map`, line config | `LineSegment[]`, orientation classes |
| D4 | Roll Estimator | horizontal / vertical lines | `roll_result` |
| D5 | Pitch Estimator | horizon candidates, camera model | `pitch_result` |
| D6 | Yaw Estimator | perspective lines, camera model | `yaw_result` |
| D7 | Pose Integrator | angle results | `pose_result` |
| D8 | Confidence Scorer | pose result, feature support | `pose_result_with_confidence` |
| D9 | Output Context | pose result, debug data | JSON, Rich Table, debug images |
| D10 | Evaluation Context | prediction, labels, artifacts | metrics report |

## 6. 小階段流程設計

```mermaid
flowchart TD
    A[Input Image File] -->|image_path| B[D1 Image Reader]
    B -->|frame_packet + bgr_frame| C[D2 Grayscale / Resize / Blur]
    C -->|preprocessed_frame| D[D2 Canny Edge Detection]
    D -->|edge_map| E[D3 HoughLinesP]
    E -->|LineSegment[]| F[D3 Line Classification]
    F -->|horizontal / vertical lines| G[D4 Roll Estimation]
    F -->|horizontal candidates| H[D5 Horizon Selection]
    F -->|perspective lines| I[D6 VP Estimation]
    H -->|horizon_result| J[D5 Pitch Estimation]
    I -->|vp_result| K[D6 Yaw Estimation]
    G -->|roll_result| L[D7 Pose Integration]
    J -->|pitch_result| L
    K -->|yaw_result| L
    L -->|pose_result| M[D8 Confidence Scoring]
    M -->|pose_result_with_confidence| N[D9 Debug / Output]
    B -->|bgr_frame| N
    F -->|line debug data| N
    H -->|horizon debug data| N
    I -->|VP debug data| N
    N -->|pose_result.json + debug png| O[D10 Verification]
```

## 7. 設計決策

| 項目 | 第一版選擇 | 原因 |
|---|---|---|
| Input | OpenCV / Pillow | OpenCV 接後續影像處理，Pillow 保留舊專案能力 |
| Edge | Canny | 可解釋，適合 HoughLinesP |
| Line | Probabilistic Hough | 直接輸出線段端點，容易 debug |
| Roll | orientation histogram / weighted median | 第一個可交付角度，容易 synthetic test |
| Pitch | horizon + focal fallback | 可從水平結構建立 baseline |
| Yaw | VP intersection / voting | 可解釋且可視化 |
| Confidence | heuristic support score | 幾何法需要避免過度宣稱 |
| Debug | staged debug artifacts | 可定位失敗來源 |

## 8. 延伸文件

```text
03_Design/system_design_breakdown.md
03_Design/bounded_context_map.md
```
