# Geometry Based Pose Analysis

## 1. 目的

本文件負責整理「若要完成 Geometry Based Pose 這個主題，需要拆成哪些分析架構與模組」。Analysis 階段不直接決定程式檔案怎麼切，而是先定義問題邊界、模組資料流、可用技術與最後流程。

第一版主線：

```text
Single Image
-> preprocessing
-> edge detection
-> line detection
-> geometry feature extraction
-> yaw / pitch / roll estimation
-> confidence
-> debug artifacts
```

第一版不宣稱精準 calibrated pose。若只使用 FOV / focal length fallback，yaw 與 pitch 必須標記為 approximate。

## 2. Analysis 架構總覽

| ID | 分析架構 | 分析重點 | Design 對應 |
|---|---|---|---|
| A1 | Image Input Analysis | 定義圖片讀取、格式驗證與 frame metadata 保存方式 | D1 Input Context |
| A2 | Preprocessing Analysis | 定義 resize、grayscale、blur、edge detection 的處理方式 | D2 Preprocessing Context |
| A3 | Line Detection Analysis | 定義 edge map 轉 line segments 的方法 | D3 Geometry Feature Context |
| A4 | Orientation / Roll Analysis | 定義如何由水平線、垂直線與方向分布估計 roll | D4 Roll Estimator |
| A5 | Horizon / Pitch Analysis | 定義如何由 horizon position 與 focal length fallback 估計 pitch | D5 Pitch Estimator |
| A6 | Vanishing Point / Yaw Analysis | 定義如何由 perspective lines 與 vanishing point 估計 yaw | D6 Yaw Estimator |
| A7 | Pose Integration Analysis | 定義 yaw / pitch / roll 整合成 PoseResult 的格式 | D7 Pose Integrator |
| A8 | Confidence Analysis | 定義 per-angle confidence 與 overall confidence 的來源 | D8 Confidence Scorer |
| A9 | Debug / Output Analysis | 定義 debug artifacts、JSON、Rich Table 與 overlay 輸出 | D9 Output Context |
| A10 | Verification Analysis | 定義 synthetic tests、manual labels、metrics 與 failure cases | D10 Evaluation Context |

## 3. 模組分析

### A1. Image Input Analysis

目標是把 `image_path` 轉成後續 OpenCV / NumPy 可處理的 frame，並保存 `image_path`、`image_width`、`image_height`、`source_format`。

需要確認：

- 檔案是否存在。
- 副檔名是否支援。
- 圖片是否可成功 decode。
- 原始 BGR frame 是否保留給 debug overlay。

### A2. Preprocessing Analysis

目標是產生穩定的幾何特徵輸入。

建議處理：

- BGR 轉 grayscale。
- resize 到固定寬度。
- Gaussian blur 降低 noise。
- Canny edge detection 產生 `EdgeMap`。
- 可選 CLAHE 或 bilateral filter。

### A3. Line Detection Analysis

目標是從 `EdgeMap` 取得 `LineSegment[]`。

第一版建議：

```text
EdgeMap
-> cv2.HoughLinesP
-> LineSegment[]
-> orientation classification
```

後續可評估 LSD、EDLines、RANSAC line fitting 與 line merging。

### A4. Orientation / Roll Analysis

Roll 是第一個可交付角度，因為它可由水平線、垂直線或線段主方向直接估計。

建議策略：

- 將 line segments 分成 near-horizontal、near-vertical、diagonal。
- 以線段長度作為權重。
- 使用 dominant orientation 或 weighted median 估計 roll。

### A5. Horizon / Pitch Analysis

Pitch 主要依賴地平線相對影像中心的位置。

建議策略：

```text
horizon_y
center_y
focal_length_pixels
pitch = atan((center_y - horizon_y) / focal_length_pixels)
```

限制：

- 地平線不一定可見。
- 室內或道路場景可能把結構線誤認成地平線。
- focal length fallback 會讓 pitch 只能近似。

### A6. Vanishing Point / Yaw Analysis

Yaw 主要依賴透視線收斂出的 vanishing point。

建議策略：

```text
perspective lines
-> pairwise intersections
-> voting / median candidate
-> dominant vanishing point
-> yaw approximation
```

限制：

- 多個 vanishing point 可能互相干擾。
- 場景不符合 Manhattan World 時 yaw 會不穩。
- VP 落在畫面外時數值容易被 focal length fallback 放大。

### A7. Pose Integration Analysis

目標是把 partial angle results 整合成 `PoseResult`。

`PoseResult` 應包含：

- yaw / pitch / roll。
- per-angle confidence。
- overall confidence。
- features_used。
- warnings。
- method。

### A8. Confidence Analysis

Confidence 不能只看是否有輸出角度，而要看特徵品質與一致性。

建議來源：

- line count。
- line length distribution。
- orientation concentration。
- horizon support。
- vanishing point support。
- angle range sanity check。
- fallback camera model 使用情況。

### A9. Debug / Output Analysis

Debug 是幾何法必要輸出，因為使用者需要知道系統根據哪些線索判斷。

建議 artifacts：

| Artifact | 說明 |
|---|---|
| `01_input.png` | 原始輸入 |
| `02_grayscale.png` | 灰階結果 |
| `04_edges.png` | Canny edge map |
| `05_detected_lines.png` | 初始線段 |
| `08_roll_candidate_lines.png` | roll 候選線 |
| `12_selected_horizon.png` | selected horizon |
| `16_selected_vanishing_point.png` | selected VP |
| `18_pose_overlay.png` | final pose overlay |

### A10. Verification Analysis

Verification 需要確認系統是否「在可用場景中穩定」，不是證明單張照片 pose 絕對正確。

建議指標：

- roll synthetic rotation error。
- horizon detection success rate。
- vanishing point stability。
- yaw / pitch / roll MAE if labels exist。
- confidence vs failure consistency。
- debug artifact completeness。

## 4. 模組溝通與資料交換流程

```mermaid
flowchart TD
    A1[A1 Image Input] -->|frame_packet: json<br/>bgr_frame: ndarray| A2[A2 Preprocessing]
    A2 -->|preprocess_result: json<br/>gray_frame: ndarray<br/>edge_map: ndarray| A3[A3 Line Detection]
    A3 -->|line_result: json<br/>LineSegment[]| A4[A4 Orientation / Roll]
    A3 -->|line_result: json<br/>LineSegment[]| A5[A5 Horizon / Pitch]
    A3 -->|perspective_lines: LineSegment[]| A6[A6 VP / Yaw]
    A4 -->|roll_result: json<br/>roll: degree<br/>roll_confidence: float| A7[A7 Pose Integration]
    A5 -->|pitch_result: json<br/>horizon: line<br/>pitch: degree<br/>pitch_confidence: float| A7
    A6 -->|yaw_result: json<br/>vanishing_point: xy<br/>yaw: degree<br/>yaw_confidence: float| A7
    A7 -->|pose_result: json<br/>yaw_pitch_roll + features_used + warnings| A8[A8 Confidence]
    A8 -->|pose_result_with_confidence: json| A9[A9 Debug / Output]
    A9 -->|pose_result.json<br/>debug_artifacts: png| A10[A10 Verification]
    A10 -->|metrics_report.json<br/>failure_cases.md| OUT[Output Artifacts]
```

## 5. 模組可用技術與工具比較

### A1. Image Input 技術

| 技術 / 工具 | 特性 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|---|
| OpenCV `cv2.imread` | 直接讀取影像為 ndarray | 與後續 OpenCV pipeline 整合最好 | HEIC 支援有限 | 採用 |
| Pillow | 支援常見圖片與 EXIF | 舊專案已有基礎 | 影像處理不如 OpenCV 直接 | 輔助 |
| pillow-heif | HEIC / HEIF 支援 | 可延續舊 metadata 能力 | 額外依賴 | 後續擴充 |

### A2. Preprocessing 技術

| 技術 / 工具 | 特性 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|---|
| `cv2.cvtColor` | BGR 轉 grayscale | 簡單穩定 | 失去顏色資訊 | 採用 |
| `cv2.resize` | 固定處理尺寸 | 加速且穩定 debug | 需保存 scale metadata | 採用 |
| Gaussian blur | Canny 前降噪 | 減少細碎雜訊 | 過度 blur 會抹掉線 | 採用 |
| CLAHE | 局部對比增強 | 低光場景可能更穩 | 可能放大 noise | 後續評估 |
| Canny | 二值 edge map | 適合接 HoughLinesP | threshold 敏感 | 採用 |

### A3. Line Detection 技術

| 技術 / 工具 | 特性 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|---|
| `cv2.HoughLinesP` | probabilistic Hough line segments | 直接輸出端點，易 debug | 參數敏感 | 採用 |
| Standard Hough | rho / theta line model | 適合全域線方向 | 需轉成可視化線段 | 不作主流程 |
| LSD | Line Segment Detector | 線段品質常較好 | OpenCV 版本支援需確認 | 後續評估 |
| EDLines | 邊緣驅動線段偵測 | 對線段偵測強 | 額外依賴成本 | 後續評估 |
| RANSAC Line Fitting | robust fitting | 可抗 outliers | 需要候選點或線段群 | 用於 horizon / VP 輔助 |

### A4-A6. Pose Feature 技術

| 技術 / 工具 | 對應角度 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|---|
| Orientation histogram | roll | 可解釋，適合 debug | 受非結構線干擾 | 採用 |
| Weighted median | roll / horizon | 對少量 outliers 穩 | 多群候選時可能錯 | 採用 |
| RANSAC horizon fitting | roll / pitch | 抗 outliers | 參數與測試成本較高 | 後續升級 |
| Pairwise VP intersection | yaw | 直觀可視化 | 對錯線段敏感 | 採用 baseline |
| VP voting / clustering | yaw | 比單一交點穩 | 多 VP 場景仍需處理 | 採用 baseline |
| Manhattan World | yaw / pitch / roll | 對建築 / 室內有力 | 自然場景不適用 | 後續評估 |

### A7-A10. Output / Verification 技術

| 技術 / 工具 | 用途 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|---|
| JSON | 保存 PoseResult 與 artifacts | 可追溯、可測試 | 需定義 schema | 採用 |
| Rich Table | CLI 可讀輸出 | 舊專案已有基礎 | 不適合大量 batch | 採用 |
| OpenCV drawing APIs | 畫 debug overlay | 與 frame pipeline 整合 | 複雜排版有限 | 採用 |
| Matplotlib | metrics / histogram | 適合 report | 不適合逐張 overlay | 驗證輔助 |
| Synthetic rotation tests | roll 驗證 | 可建立明確 ground truth | 只驗證 roll | 採用 |

## 6. 小階段工具使用整理

| ID | 小階段 | What 使用工具 | Why 使用原因 | How 使用方式 | How-to 實作重點 |
|---|---|---|---|---|---|
| A1 | Image Input | OpenCV `cv2.imread` / Pillow | 取得原始 frame 與 metadata | 讀取 `image_path` 並建立 `frame_packet` | 保留原圖尺寸與 source format |
| A2 | Grayscale | `cv2.cvtColor` | edge / line detection 不需要 RGB | BGR 轉 gray | 原 BGR 留給 overlay |
| A2 | Resize | `cv2.resize` | 加速與穩定參數 | 依 config resize | 保存 `scale_meta` |
| A2 | Blur | `cv2.GaussianBlur` | 降低 Canny noise | gray frame blur | kernel 不宜過大 |
| A2 | Edge Detection | `cv2.Canny` | 產生 line detection input | blur frame 轉 edge map | threshold 需可調 |
| A3 | Line Detection | `cv2.HoughLinesP` | 直接取得線段端點 | edge map 轉 lines | 保存 length / angle |
| A3 | Line Classification | NumPy | roll / horizon / VP 需要不同線段 | 依 angle 分類 | 保存 near-horizontal / vertical / diagonal |
| A4 | Roll Estimation | orientation histogram / weighted median | roll 最容易先交付 | 用水平 / 垂直線估主方向 | 輸出 roll confidence |
| A5 | Horizon Selection | weighted horizon / RANSAC fallback | pitch 需要 horizon_y | 從水平線選 candidate | 保存 candidate score |
| A5 | Pitch Estimation | focal length fallback + `atan` | horizon_y 可近似 pitch | 用 `center_y - horizon_y` 計算 | 標記 approximate |
| A6 | VP Estimation | pairwise intersections / voting | yaw 需要 vanishing point | diagonal lines 延伸交點投票 | 保存 VP candidates |
| A6 | Yaw Estimation | focal length fallback + `atan` | VP x 偏移可近似 yaw | 用 `vp_x - center_x` 計算 | 標記 approximate |
| A7 | Pose Integration | JSON schema | 整合 partial results | 合併 yaw / pitch / roll | 允許 partial null |
| A8 | Confidence | heuristic scoring | 避免誤信錯誤角度 | 根據 support / consistency 計分 | per-angle + overall |
| A9 | Debug Output | OpenCV drawing + JSON / Rich | 可解釋結果 | 產生 debug png 與 pose JSON | artifact path 要可追 |
| A10 | Verification | synthetic tests / metrics | 確認穩定性 | 比對 labels 或合成資料 | 輸出 metrics report |

## 7. 最終步驟與資料傳遞流程

此流程圖以第 6 節「小階段工具使用整理」為節點來源，重點放在每個小階段傳遞給下一個小階段的資料格式。

```mermaid
flowchart TD
    A[Input Image File] -->|image_path: jpg/png| B[A1 Image Reader]
    B -->|frame_packet: json<br/>bgr_frame: ndarray| C[A2 Grayscale]
    C -->|gray_frame: ndarray| D[A2 Resize / Blur]
    D -->|preprocessed_frame: ndarray<br/>scale_meta: json| E[A2 Canny Edge Detection]
    E -->|edge_map: ndarray| F[A3 HoughLinesP]
    F -->|line_result: json<br/>LineSegment[]| G[A3 Line Classification]
    G -->|horizontal / vertical lines| H[A4 Roll Estimation]
    G -->|horizontal candidates| I[A5 Horizon Selection]
    G -->|diagonal / perspective lines| J[A6 VP Estimation]
    H -->|roll_result: json| K[A7 Pose Integration]
    I -->|horizon_result: json| L[A5 Pitch Estimation]
    J -->|vp_result: json| M[A6 Yaw Estimation]
    L -->|pitch_result: json| K
    M -->|yaw_result: json| K
    K -->|pose_result: json| N[A8 Confidence Scoring]
    N -->|pose_result_with_confidence: json| O[A9 Debug / Output]
    B -->|bgr_frame: ndarray| O
    F -->|detected lines| O
    I -->|horizon candidate| O
    J -->|VP candidates| O
    O -->|pose_result.json<br/>debug_artifacts: png| P[A10 Verification]
    P -->|metrics_report.json<br/>failure_cases.md| Q[Output Artifacts]
```

## 8. Analysis 到 Design 的對應原則

- Analysis 的 A1 到 A10 必須在 Design 中有對應模組或 bounded context。
- 模組之間必須透過明確資料物件交換，例如 `FramePacket`、`EdgeMap`、`LineSegment[]`、`FeatureSet`、`PoseResult`。
- 若 Design 新增模組，必須標明它支援哪一個 Analysis ID。
- 若未來加入 calibrated camera model，只應替換 camera model / pose formula，不應重寫整條 pipeline。

## 9. 延伸文件

既有詳細分析保留於：

```text
02_Analysis/geometry_pose_analysis.md
02_Analysis/technology_selection_rationale.md
```

