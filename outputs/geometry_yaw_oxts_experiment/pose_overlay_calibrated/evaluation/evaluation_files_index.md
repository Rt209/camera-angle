# Geometry Pose Evaluation 檔案索引

此 evaluation 目錄整理 geometry pose 的 pitch、yaw、roll 評估資料，並保留 yaw calibration transform 的中間結果。

## 類 optical-flow 架構

主要輸出也同步整理在：

```text
outputs/geometry_yaw_oxts_experiment/pose_overlay_calibrated/
```

其結構對齊：

```text
outputs/optical_flow_pose/pose_overlay_uncalibrated/
```

包含：

- `pose_timeline.csv`
- `frame_pose_results.json`
- `output_pose_overlay.mp4`
- `debug_frames/`
- `evaluation/`

## Evaluation 檔案

| 檔案 | 用途 |
|---|---|
| `evaluation_report.md` | 完整 pitch/yaw/roll 評估報告，格式仿 optical-flow evaluation report。 |
| `integrated_pose_vs_oxts.csv` | pitch、yaw、roll 整合逐 frame comparison。 |
| `integrated_pose_summary.json` | pitch、yaw、roll 整合 summary，包含 MAE/RMSE、segments、worst frames。 |
| `integrated_pose_report.md` | pitch、yaw、roll 整合短報告。 |
| `calibrated_pose_vs_oxts.csv` | yaw calibration transform 後的逐 frame yaw comparison。 |
| `yaw_calibration_summary.json` | yaw calibration model 與 before/after summary。 |
| `yaw_calibration_report.md` | yaw calibration transform 評估報告。 |
| `pose_vs_oxts_debug_comparison.csv` | reliability gate 與 yaw debug comparison。 |
| `new_pipeline_summary.json` | reliability gate summary。 |
| `confidence_failure_report.json` | high confidence + high yaw error failure 統計。 |

## 圖表

| 圖表 | 用途 |
|---|---|
| `calibrated_yaw_pred_vs_oxts.png` | calibrated yaw 與 OXTS yaw 時序比較。 |
| `raw_vs_calibrated_yaw_error.png` | current yaw error 與 calibrated yaw error 比較。 |
| `calibrated_confidence_vs_abs_error.png` | calibration 後 confidence vs yaw absolute error。 |
| `yaw_pred_vs_oxts.png` | current yaw 與 OXTS yaw 時序比較。 |
| `pitch_pred_vs_oxts.png` | pitch 與 OXTS pitch 時序比較。 |
| `roll_pred_vs_oxts.png` | roll 與 OXTS roll 時序比較。 |
| `abs_error_by_frame.png` | pitch/yaw/roll absolute error by frame。 |
| `confidence_vs_abs_error.png` | current confidence vs absolute error。 |

## 整體指標

```text
Yaw MAE current:     34.3517 deg
Yaw MAE calibrated:  20.9250 deg
Pitch MAE:           1.3891 deg
Roll MAE:            1.5228 deg

Yaw RMSE current:    40.3713 deg
Yaw RMSE calibrated: 26.2045 deg
Pitch RMSE:          1.8433 deg
Roll RMSE:           1.9023 deg

Confidence failure before: 17
Confidence failure after:  0
```
