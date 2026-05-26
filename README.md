# visual-pose-angle-detector

這是一個 Python CLI 專案，用來從單張圖片的影像內容估計視覺姿態角度。

目前主要進度是 **Stage 4-7：Pose Integration and Debug**。預設 pipeline 會執行圖片輸入、前處理、直線偵測、horizon detection、vanishing point detection，並輸出 `yaw`、`pitch`、`roll`、confidence 與 debug images。

舊版 Stage 0-3 roll-only pipeline 仍可透過 `--stage-0-3` 執行。EXIF / metadata 報告功能仍保留，可透過 `--metadata` 執行。

## 目前完成範圍

Stage 4-7 pipeline：

```text
單張圖片
-> 讀取圖片
-> 前處理
-> 邊緣偵測
-> 直線偵測
-> Roll estimation
-> Horizon detection + Pitch estimation
-> Vanishing point detection + Yaw estimation
-> PoseResult + confidence
-> Rich Table / JSON / debug images
```

目前不處理：

- batch validation / metrics report
- video input
- realtime camera input
- deep learning-based pose estimation
- automatic camera calibration

## 測試圖片來源

`examples/0.png` 是用於 Stage 4-7 regression 與 debug 流程的測試圖片，來源為 [KITTI Vision Benchmark Suite](https://www.cvlibs.net/datasets/kitti/)。

KITTI 由 Karlsruhe Institute of Technology 與 Toyota Technological Institute at Chicago 建立，官方頁面說明資料集用於真實世界電腦視覺 benchmark，涵蓋 stereo、optical flow、visual odometry、3D object detection、tracking 等任務。

請注意：KITTI 官方頁面標示資料集與 benchmark 採用 **Creative Commons Attribution-NonCommercial-ShareAlike 3.0** 授權。此專案中的測試圖片僅用於本地開發、除錯與非商用研究用途；若後續公開發佈或使用於研究，請依 KITTI 官方要求標註來源與引用。

本專案同時保存：

```text
examples/0.png
examples/picture_information.txt
breakdown/06_Debug/examples_0_pose_debug_process.md
breakdown/06_Debug/examples_0_artifacts/
```

其中 `picture_information.txt` 記錄該圖片對應的 yaw / pitch / roll 參考值，`breakdown/06_Debug/` 則保存本案例的 debug 分析流程與代表性 artifact。

## 專案結構

```text
camera-angle/
├─ main.py
├─ pyproject.toml
├─ requirements.txt
├─ README.md
├─ examples/
├─ breakdown/
├─ src/
│  ├─ app/
│  │  └─ pipeline.py
│  ├─ cli/
│  │  ├─ parser.py
│  │  └─ commands.py
│  ├─ contexts/
│  │  ├─ input/
│  │  ├─ preprocessing/
│  │  ├─ geometry_features/
│  │  ├─ pose_estimation/
│  │  └─ output/
│  ├─ io/
│  ├─ metadata/
│  ├─ output/
│  ├─ processing/
│  └─ shared/
└─ tests/
```

## 安裝

建議使用 Python 3.10 以上版本。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

或使用 editable install：

```bash
pip install -e ".[dev]"
```

## CLI 使用方式

查看說明：

```bash
python main.py --help
```

執行預設 Stage 4-7 visual pose pipeline：

```bash
python main.py --path examples/0.png
```

輸出 JSON：

```bash
python main.py --path examples/0.png --json
```

將 JSON 寫入檔案：

```bash
python main.py --path examples/0.png --json --output result.json
```

指定 debug 圖輸出資料夾：

```bash
python main.py --path examples/0.png --debug-dir debug/stage4-7
```

執行 Stage 0-3 roll-only pipeline：

```bash
python main.py --path examples/0.png --stage-0-3
```

執行舊版 EXIF / metadata 報告：

```bash
python main.py --path examples/0.png --metadata
```

## 支援圖片格式

- `.jpg`
- `.jpeg`
- `.png`
- `.heic`
- `.heif`
- `.tif`
- `.tiff`

## Stage 4-7 JSON 輸出重點

Stage 4-7 的輸出會包含：

```json
{
  "image": "0.png",
  "yaw": -64.8,
  "pitch": 1.57,
  "roll": 1.89,
  "unit": "degree",
  "confidence": 0.89,
  "method": "geometry_based_pose_estimation",
  "stage": "stage_4_7_pose_integration_and_debug",
  "features_used": ["edges", "lines", "vertical_lines", "horizon", "vanishing_point"],
  "angle_confidence": {
    "yaw": 0.9,
    "pitch": 0.85,
    "roll": 0.92
  },
  "debug_artifacts": {},
  "warnings": [],
  "line_features": {},
  "horizon_features": {},
  "vanishing_point_features": {}
}
```

實際數值會依圖片內容與偵測結果而變動。若某個角度無法估計，該欄位會是 `null`，對應的 confidence 會是 `0.0`，並在 `warnings` 中說明原因。

## Debug Images

預設 pipeline 會產生下列 debug 圖：

| Key | 檔名 | 用途 |
| --- | --- | --- |
| `input` | `01_input.png` | 輸入圖片 |
| `grayscale` | `02_grayscale.png` | 灰階結果 |
| `blurred` | `03_blurred.png` | 模糊降噪結果 |
| `edges` | `04_edges.png` | 邊緣偵測結果 |
| `detected_lines` | `05_detected_lines.png` | Hough 偵測到的原始線段 |
| `lines` | `06_filtered_lines.png` | 過濾後線段 |
| `line_orientation_debug` | `07_line_orientation_debug.png` | 線段方向分類 |
| `roll_candidate_lines` | `08_roll_candidate_lines.png` | 用於 roll 的候選線段 |
| `roll_orientation_histogram` | `09_roll_orientation_histogram.png` | roll 候選角度分布 |
| `roll_overlay` | `10_roll_overlay.png` | roll 估計結果 |
| `horizon_candidates` | `11_horizon_candidates.png` | horizon 候選線 |
| `horizon` | `12_selected_horizon.png` | selected horizon |
| `pitch_overlay` | `13_pitch_overlay.png` | pitch 估計結果 |
| `perspective_lines` | `14_perspective_lines.png` | 用於 vanishing point 的線段 |
| `vanishing_point_candidates` | `15_vanishing_point_candidates.png` | vanishing point 候選交點 |
| `vanishing_point` | `16_selected_vanishing_point.png` | selected vanishing point |
| `yaw_overlay` | `17_yaw_overlay.png` | yaw 估計結果 |
| `pose_overlay` | `18_pose_overlay.png` | yaw / pitch / roll 最終疊圖 |

根目錄 `debug/` 是本機執行產物，已被 `.gitignore` 忽略。若需要保留代表性 debug 結果，請放在 `breakdown/06_Debug/` 並搭配分析文件說明。

## 測試

```bash
pytest
```

目前測試涵蓋檔案驗證、EXIF 讀取、數值轉換、roll estimation、Stage 0-3 pipeline 與 Stage 4-7 pose integration pipeline。

## KITTI 影片與姿態評估輸出

本專案目前包含一組 KITTI 測試影像 / OXTS 姿態資料，並提供內建工具將 KITTI frame 轉成影片。

### 內建工具產生的 KITTI 姿態 overlay 影片

檔案位置：

```text
tools/output/kitti_pose_overlay.mp4
```

說明：

這支影片是由內建工具 `tools/kitti_pose_video.py` 將 `tools/input/images/` 的 KITTI 影像序列與 `tools/input/oxts/` 的官方 yaw / pitch / roll 姿態資料合成而來。

它的用途是人工對照與 debug reference。影片左上角會顯示 KITTI OXTS 官方姿態數值。

可重新產生：

```bash
python tools/kitti_pose_video.py --images tools/input/images --poses tools/input/oxts --output tools/output/kitti_pose_overlay.mp4
```

如果要產生沒有文字 overlay 的輸入影片，可使用：

```bash
python tools/kitti_pose_video.py --images tools/input/images --poses tools/input/oxts --output tools/output/kitti_no_overlay.mp4 --no-overlay
```

注意：

```text
tools/output/kitti_pose_overlay.mp4
```

不應作為 geometry pose pipeline 的主要演算法輸入，因為影片上的文字 overlay 會污染 edge / line detection。

### Geometry pipeline 預測結果 overlay 影片

檔案位置：

```text
outputs/video_pose/predicted_pose_overlay.mp4
```

說明：

這支影片是目前離線影片姿態偵測 pipeline 的輸出。它使用 geometry-based pipeline 對影片 frame 做 yaw / pitch / roll 預測，並將 predicted pose、confidence、status 疊到輸出影片上。

目前主要輸入影片為：

```text
tools/output/kitti_no_overlay.mp4
```

可重新產生：

```bash
python main.py --video tools/output/kitti_no_overlay.mp4 --sample-every 1 --output-dir outputs/video_pose --write-overlay
```

相關輸出：

```text
outputs/video_pose/pose_timeline.csv
outputs/video_pose/frame_pose_results.json
outputs/video_pose/predicted_pose_overlay.mp4
```

### 評估報告

影片姿態偵測結果與 KITTI OXTS 官方姿態資料的比較報告位於：

```text
outputs/video_pose/evaluation/evaluation_report.md
```

該文件整理了：

- `pose_vs_oxts.csv` 的逐幀誤差表
- `pose_vs_oxts_summary.json` 的整體統計
- `worst_frames.csv` 的最大誤差 frame
- yaw / pitch / roll predicted vs OXTS 圖片
- confidence vs absolute error 圖片
- 目前實驗結果的初步解讀
