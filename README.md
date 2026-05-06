# photo-metadata-geometry-analyzer

這是一個第一版 Python CLI 影像 metadata 分析專案。目標是穩定讀取 JPEG / HEIC / HEIF / TIFF 圖片中的 EXIF / Metadata，整理常見攝影參數，並以終端機表格或 JSON 輸出。

本專案採用「Exif standard by JEITA / CIPA」作為現代 EXIF 規格描述脈絡；歷史上 EXIF 與 JEIDA 有關，但文件與架構命名避免只寫 JEIDA。

## 專案目錄結構

```text
photo-metadata-geometry-analyzer/
├─ main.py
├─ pyproject.toml
├─ requirements.txt
├─ README.md
├─ examples/
├─ src/
│  ├─ cli/
│  │  ├─ parser.py
│  │  └─ commands.py
│  ├─ io/
│  │  ├─ file_validator.py
│  │  └─ image_loader.py
│  ├─ metadata/
│  │  ├─ exif_reader.py
│  │  ├─ tag_mapper.py
│  │  └─ metadata_model.py
│  ├─ processing/
│  │  ├─ value_converter.py
│  │  └─ metadata_normalizer.py
│  ├─ geometry/
│  │  ├─ fov.py
│  │  ├─ camera_model.py
│  │  └─ pose_estimation.py
│  ├─ output/
│  │  ├─ rich_table.py
│  │  └─ json_writer.py
│  └─ utils/
└─ tests/
   ├─ test_file_validator.py
   ├─ test_value_converter.py
   └─ test_exif_reader.py
```

## 模組職責

- `main.py`：CLI 入口點。
- `src/cli/parser.py`：定義 `--path`、`--json`、`--output` 等參數。
- `src/cli/commands.py`：串接檔案驗證、EXIF 讀取、輸出與錯誤處理。
- `src/io/file_validator.py`：驗證路徑存在、是檔案、且副檔名支援。
- `src/io/image_loader.py`：透過 Pillow 開啟圖片，並獨立註冊 HEIC / HEIF 支援。
- `src/metadata/exif_reader.py`：讀取 EXIF、整理欄位分組、產生 warnings。
- `src/metadata/tag_mapper.py`：將 EXIF tag 與 enum 數值轉成可讀文字。
- `src/metadata/metadata_model.py`：定義結構化 metadata report。
- `src/processing/value_converter.py`：處理分數、曝光時間、光圈、焦距與 EV 格式。
- `src/geometry/fov.py`：提供基礎 FOV 計算函式。
- `src/geometry/camera_model.py`：預留設備校準 profile。
- `src/geometry/pose_estimation.py`：預留仰角與姿態估算模組。
- `src/output/rich_table.py`：輸出 Rich Table。
- `src/output/json_writer.py`：輸出 JSON 字串或檔案。
- `tests/`：基本單元測試。

## 安裝

建議使用 Python 3.10 以上版本。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

或使用 pyproject：

```bash
pip install -e ".[dev]"
```

## 使用方式

顯示 Rich Table：

```bash
python main.py --path examples/IMG_001.HEIC
```

輸出 JSON 到終端機：

```bash
python main.py --path examples/IMG_001.HEIC --json
```

保存 JSON：

```bash
python main.py --path examples/IMG_001.HEIC --json --output result.json
```

## 輸出區塊

- `File Info`
- `Device Info`
- `Optical Parameters`
- `Exposure Parameters`
- `Image Parameters`
- `GPS / Direction`
- `Derived Geometry`
- `Warnings`

EXIF 缺少的欄位會顯示 `N/A`，不會讓程式直接崩潰。

## EXIF 能提供什麼

EXIF 通常可以提供：

- 焦距 `FocalLength`
- 光圈 `FNumber`
- 曝光時間 `ExposureTime`
- ISO `ISOSpeedRatings` 或 `PhotographicSensitivity`
- 曝光補償、曝光模式、測光模式、白平衡
- 相機或手機廠牌、設備型號、軟體版本
- 影像寬高、解析度、方向
- 若拍攝設備有寫入 GPS，可能包含緯度、經度、高度與 `GPSImgDirection`

## EXIF 不能保證提供什麼

EXIF 不一定能直接提供：

- 精準 FOV：只知道焦距仍不夠，還需要感光元件尺寸或設備校準資料。
- 精準仰角：單張照片通常無法只靠 EXIF 得到仰角，需要 IMU、姿態資料、地平線偵測、消失點或相機校準資訊。
- 真實拍攝方向：只有在 EXIF 真的包含 `GPSImgDirection` 時才可輸出方向角，不能憑空推論。
- 完整真實深度：單張普通照片無法只靠 EXIF 得到深度。未來可考慮 monocular depth estimation、stereo、structured light 或已知物體尺寸推估。

## 範例輸出

```text
File Info
Field      Value
filename   IMG_001.HEIC
format     HEIF

Optical Parameters
Field                    Value
FocalLength              24mm
FNumber                  f/1.8
LensModel                iPhone lens
FocalLengthIn35mmFilm    26mm

Derived Geometry
Field           Value
HorizontalFOV   N/A
VerticalFOV     N/A
PitchAngle      Unavailable from EXIF only
Depth           Unavailable from a single ordinary EXIF photo
```

## 下一階段擴充方向

1. 建立設備校準資料庫，依 `Make` / `Model` / `LensModel` 對應 sensor size，再計算水平與垂直 FOV。
2. 支援讀取更多廠商私有 metadata，例如 iPhone motion metadata 或 MakerNote，但需注意格式差異。
3. 加入方向角處理：只有在 `GPSImgDirection` 存在時輸出，並可轉換為 N / NE / E 等方位文字。
4. 加入仰角估算模組：從 IMU、地平線偵測或消失點分析取得支撐資料後再計算。
5. 加入深度分析模組：可從 stereo、monocular depth estimation、structured light 或已知物體尺寸逐步擴充。
6. 若未來要做投影或 structured light，可把 projector 視為 inverse camera，擴充 camera/projector intrinsics、extrinsics、depth map 與 projection mapping pipeline。

## 測試

```bash
pytest
```
