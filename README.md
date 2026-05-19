# visual-pose-angle-detector

這是一個 Python CLI 專案，用來從單張圖片的影像內容中估計視覺姿態角度。

目前專案進度是 **Stage 0-3：Foundation and Roll Estimation**。此階段已完成圖片輸入、前處理、邊緣偵測、直線偵測與初版 `roll` 估計。

目前尚未實作 `yaw` 與 `pitch`，所以輸出中這兩個欄位會是 `null`。舊版 EXIF / metadata 報告功能仍保留，可透過 `--metadata` 執行。

## 目前完成範圍

Stage 0-3 pipeline：

```text
單張圖片
-> 讀取圖片
-> 前處理
-> 邊緣偵測
-> 直線偵測
-> Roll estimation
-> Rich Table / JSON / debug images
```

目前不處理：

- `pitch` estimation
- `yaw` estimation
- horizon detection
- vanishing point detection
- batch validation / metrics
- video input
- realtime camera input

## 專案結構

```text
camera-angle/
├─ main.py
├─ pyproject.toml
├─ requirements.txt
├─ README.md
├─ examples/
├─ debug/
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

執行 Stage 0-3 visual pose pipeline：

```bash
python main.py --path examples/1.jpg
```

輸出 JSON：

```bash
python main.py --path examples/1.jpg --json
```

將 JSON 寫入檔案：

```bash
python main.py --path examples/1.jpg --json --output result.json
```

指定 debug 圖輸出資料夾：

```bash
python main.py --path examples/1.jpg --debug-dir debug/stage0-3
```

執行舊版 EXIF / metadata 報告：

```bash
python main.py --path examples/1.jpg --metadata
```

如果沒有提供 `--path`，程式會嘗試從 `examples/` 中尋找一張支援格式的圖片。若 `examples/` 中有多張圖片，程式會要求使用 `--path` 明確指定。

## 支援圖片格式

- `.jpg`
- `.jpeg`
- `.png`
- `.heic`
- `.heif`
- `.tif`
- `.tiff`

## Stage 0-3 JSON 輸出格式

Stage 0-3 的輸出欄位會固定包含：

```json
{
  "image": "1.jpg",
  "yaw": null,
  "pitch": null,
  "roll": 1.23,
  "unit": "degree",
  "confidence": 0.75,
  "method": "geometry_based_partial_pose_estimation",
  "stage": "stage_0_3_foundation_and_roll",
  "features_used": ["edges", "lines"],
  "debug_artifacts": {
    "input": "debug/01_input.png",
    "grayscale": "debug/02_grayscale.png",
    "blurred": "debug/03_blurred.png",
    "edges": "debug/04_edges.png",
    "detected_lines": "debug/05_detected_lines.png",
    "lines": "debug/06_filtered_lines.png",
    "line_orientation_debug": "debug/07_line_orientation_debug.png",
    "roll_candidate_lines": "debug/08_roll_candidate_lines.png",
    "roll_orientation_histogram": "debug/09_roll_orientation_histogram.png",
    "roll_overlay": "debug/10_roll_overlay.png"
  },
  "warnings": [],
  "line_features": {
    "detected_line_count": 12,
    "filtered_line_count": 8,
    "near_horizontal_count": 5,
    "near_vertical_count": 3,
    "lines": []
  }
}
```

注意：`roll` 可能是數字，也可能因為圖片缺少穩定直線而是 `null`。

## Debug Images

執行 visual pose pipeline 時會輸出下列 debug 圖：

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
| `roll_overlay` | `10_roll_overlay.png` | roll 與 confidence 疊圖 |

## 測試

```bash
pytest
```

目前測試涵蓋檔案驗證、EXIF 讀取、數值轉換、roll estimation 與 Stage 0-3 visual pose pipeline。
