# Optical Evaluation：CMD 執行方式

本文件適用於 Windows CMD，提示字元通常如下：

```text
C:\Users\GIGABYTE\camera-angle>
```

以下指令不適用 PowerShell。請從專案根目錄執行。

## 1. 設定資料與輸出位置

```cmd
set "DATASET=C:\Users\GIGABYTE\camera-angle\data\datasets\kitti\demo"
set "RUN=C:\Users\GIGABYTE\camera-angle\outputs\demo_optical_eval"
```

設定後請在同一個 CMD 視窗確認變數已生效：

```cmd
echo %DATASET%
echo %RUN%
```

輸出必須是完整路徑，不能仍顯示 `%DATASET%` 或 `%RUN%`。CMD 變數只存在於目前視窗；如果關閉並重新開啟 CMD，必須重新執行上述兩行 `set`。

如果不想覆蓋前一次結果，可以修改 `RUN` 名稱，例如：

```cmd
set "RUN=C:\Users\GIGABYTE\camera-angle\outputs\demo_optical_eval_02"
```

## 2. 將照片合成無標註影片

```cmd
python tools\dataset\kitti_pose_video.py --images "%DATASET%\images" --poses "%DATASET%\references\oxts" --output "%RUN%\input\image_sequence.mp4" --fps 10 --no-overlay
```

`--no-overlay` 代表輸入影片不會畫入 OXTS 正確答案。

## 3. 執行 Optical Flow 姿態分析

```cmd
python tools\optical_flow\write_uncalibrated_pose_overlay.py --video "%RUN%\input\image_sequence.mp4" --debug-dir "%RUN%\optical" --kitti-calibration-dir "%DATASET%\calibration" --kitti-camera-index 03
```

Debug frames 預設關閉，不會產生大量除錯圖片。

## 4. 產生 Optical 評估報告

```cmd
python tools\evaluation\evaluate_uncalibrated_pose_overlay_against_oxts.py --pose-json "%RUN%\optical\frame_pose_results.json" --oxts-dir "%DATASET%\references\oxts" --output-dir "%RUN%\eval\optical" --kitti-calibration-dir "%DATASET%\calibration" --kitti-camera-index 03 --save-plots --save-worst-frames
```

## 5. 查看結果

主要輸出位於：

```text
outputs/demo_optical_eval/
├── input/
│   └── image_sequence.mp4
├── optical/
│   ├── pose_overlay.mp4
│   ├── pose_timeline.csv
│   └── frame_pose_results.json
└── eval/
    └── optical/
        ├── evaluation_report.md
        ├── summary.json
        ├── per_frame.csv
        ├── worst_frames.csv
        └── plots/
```

## 報告語言注意事項

目前 `evaluation_report.md` 的產生模板仍為英文，CLI 也還沒有語言參數。若驗收要求繁體中文，需要先將 Evaluation Markdown report writer 本地化；CSV 與 JSON 欄位建議維持英文，避免破壞現有工具與測試相容性。
