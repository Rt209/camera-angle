# Tools 使用指南

`tools` 保存可直接從命令列執行的開發、分析與驗證工具。正式的商業邏輯放在 `src`；這裡的腳本主要負責組合既有服務、讀取資料與產生報告。

## 資料夾結構

```text
tools/
├── calibration/   # 相機內參校正
├── dataset/       # KITTI 等資料集轉換與影片產生
├── evaluation/    # 預測姿態與參考資料的比較
├── geometry/      # Geometry-based pose 實驗
├── optical_flow/  # Optical Flow pose 分析、Overlay 與調參
├── input/         # 範例輸入資料
├── output/        # 工具產生的範例影片
└── README.md
```

## 工具索引

| 分類 | 工具 | 用途 |
|---|---|---|
| Calibration | `calibration/calibrate_camera_from_video.py` | 從棋盤格或 Charuco 影片建立相機內參 |
| Dataset | `dataset/kitti_pose_video.py` | 將 KITTI 影像與 OXTS 姿態組成影片 |
| Evaluation | `evaluation/evaluate_video_pose_against_oxts.py` | 比較 Geometry-based pose 與 OXTS |
| Evaluation | `evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py` | 比較 Optical Flow relative pose 與 OXTS 變化趨勢 |
| Geometry | `geometry/run_geometry_yaw_oxts_experiment.py` | 執行 geometry yaw 與 OXTS 實驗 |
| Geometry | `geometry/run_geometry_yaw_calibration_experiment.py` | 執行 geometry yaw 校正實驗 |
| Geometry | `geometry/write_geometry_integrated_pose_evaluation.py` | 整合 geometry pose 評估結果 |
| Optical Flow | `optical_flow/analyze_optical_flow_paths.py` | 分析 sparse flow 路徑、速度與方向 |
| Optical Flow | `optical_flow/write_uncalibrated_pose_overlay.py` | 產生 approximate-K pose Overlay |
| Optical Flow | `optical_flow/debug_optical_flow_pose_parameters.py` | 比較 LK 與 RANSAC 參數組合 |

## 常用命令

請從 repository 根目錄執行：

```powershell
# 建立 KITTI 測試影片
python tools/dataset/kitti_pose_video.py `
  --images tools/input/images `
  --poses tools/input/oxts `
  --output tools/output/kitti_no_overlay.mp4 `
  --no-overlay

# 分析 Optical Flow 路徑
python tools/optical_flow/analyze_optical_flow_paths.py `
  --video tools/output/kitti_no_overlay.mp4 `
  --debug-dir outputs/optical_flow_pose/sparse_flow

# 產生 Optical Flow pose Overlay
python tools/optical_flow/write_uncalibrated_pose_overlay.py `
  --video tools/output/kitti_no_overlay.mp4 `
  --debug-dir outputs/optical_flow_pose/pose_overlay_uncalibrated

# 執行 Optical Flow pose 評估
python tools/evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py `
  --pose-json outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json `
  --oxts-dir tools/input/oxts `
  --output-dir outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation
```

## 維護原則

- 腳本只負責流程組合；可重用邏輯應放在 `src`。
- 新工具必須放入對應功能資料夾，不直接堆在 `tools` 根目錄。
- 輸入範例放在 `input`；可重建的產物放在 `output` 或 repository 根目錄的 `outputs`。
- 新增或移動工具時，必須同步更新 `tests/tooling`、本 README 與 breakdown 文件中的命令。

