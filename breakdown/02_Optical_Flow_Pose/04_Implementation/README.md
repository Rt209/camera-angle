# Optical Flow Pose Implementation Plan

## 1. 目的

本文件規劃 optical flow camera-pose pipeline 的實作階段。新的第一版要求是：不讓一般使用者輸入 FOV、`f_x`、`f_y`，而是先用 calibration video 透過 `cv2.calibrateCamera` 取得 camera intrinsics。

## 2. Phase Overview

| Phase | 名稱 | 目標 |
|---|---|---|
| Phase 0 | Project Setup | 建立專案結構、設定 config |
| Phase 1 | Calibration Video I/O | 讀取棋盤格或 Charuco board calibration video |
| Phase 2 | Calibration Pattern Detection | 偵測 calibration board corners |
| Phase 3 | Camera Calibration | 使用 `cv2.calibrateCamera` 建立 `K` 與 distortion coefficients |
| Phase 4 | Pose Video I/O | 完成 pose video 讀取、逐幀處理、影片寫出 |
| Phase 5 | Preprocessing | undistort、灰階、resize、Gaussian blur |
| Phase 6 | Feature Detection | 使用 Shi-Tomasi 偵測可追蹤角點 |
| Phase 7 | Optical Flow Tracking | 使用 Lucas-Kanade optical flow 追蹤前後幀特徵點 |
| Phase 8 | Geometry Estimation | 使用 Essential Matrix + RANSAC 過濾 outliers |
| Phase 9 | Pose Recovery | 使用 recoverPose 得到 `R`, `t`，並將 `R` 轉 yaw / pitch / roll |
| Phase 10 | Visualization and Logging | 疊加光流、姿態資訊，輸出影片與 CSV / JSON |
| Phase 11 | Verification | 使用測試影片或 ground truth 驗證結果 |

## 3. Phase Details

| Phase | 目標 | 輸入 | 輸出 | 主要函式或模組 | 完成條件 | 可能風險 |
|---|---|---|---|---|---|---|
| 0 | 建立結構與 config | project root | module folders、config schema | `config.py` | config 可載入預設參數 | 過早設計過多參數 |
| 1 | 讀 calibration video | calibration video path | calibration frames | `calibration_video_reader.py` | 可抽取清楚 frames | blur 或 board 太小 |
| 2 | 偵測 board corners | calibration frames | object points、image points | `board_detector.py` | 足夠 frames 偵測成功 | board 設定錯誤 |
| 3 | 建立 `K` | object/image points、frame size | `camera_intrinsics.json` | `camera_calibrator.py` | reprojection error 合理 | calibration 覆蓋範圍不足 |
| 4 | 影片讀寫 | pose video path | frame stream、output writer | `reader.py`, `writer.py` | 可讀入並寫出同尺寸影片 | codec 不支援 |
| 5 | 前處理 | BGR frame、`K`、`dist_coeffs` | undistorted gray frame | `frame_preprocessor.py` | undistort / resize 正確 | resize 未同步 K |
| 6 | 偵測角點 | gray frame | feature points | `feature_detector.py` | 可取得足夠角點 | 低紋理場景點數不足 |
| 7 | LK tracking | prev/curr gray、points | point correspondences | `lk_tracker.py` | 可畫出 tracks | motion blur 追蹤錯誤 |
| 8 | 幾何估計 | matched points、`K` | `E`、inlier mask | `essential_matrix.py` | inlier ratio 合理 | 動態物體污染 |
| 9 | 姿態恢復 | `E`、points、`K` | `R`, `t`, Euler angles | `pose_recovery.py`, `euler_angles.py` | yaw/pitch/roll 不爆值 | Euler convention mismatch |
| 10 | 視覺化與 log | frame、flow、pose stats | video、CSV、JSON | visualization、logger | 可追溯每幀狀態 | overlay 資訊過多 |
| 11 | 驗證 | output、ground truth optional | metrics report | `verification/metrics.py` | 可判斷成功/失敗 | 無 ground truth 時只能定性 |

## 4. 建議 Config

```yaml
calibration:
  calibration_video_path: null
  calibration_pattern: charuco
  board_rows: 7
  board_cols: 10
  square_size: 1.0
  min_valid_frames: 20
  output_intrinsics: outputs/calibration/camera_intrinsics.json

video:
  pose_video_path: null
  frame_step: 1
  resize_width: 960
  output_codec: mp4v

features:
  max_corners: 1000
  quality_level: 0.01
  min_distance: 8

lk:
  win_size: [21, 21]
  max_level: 3
  criteria_count: 30
  criteria_eps: 0.01

ransac:
  threshold: 1.0
  probability: 0.999

pose:
  smoothing: moving_average
  smoothing_window: 5
```

## 5. Output Artifacts

```text
outputs/calibration/camera_intrinsics.json
outputs/calibration/calibration_report.md
outputs/calibration/debug/detected_corners/
outputs/optical_flow_pose/output_overlay.mp4
outputs/optical_flow_pose/pose_timeline.csv
outputs/optical_flow_pose/frame_pose_results.json
outputs/optical_flow_pose/debug/
```

## 6. CLI 草案

第一版建議分成兩步：

```bash
python tools/calibrate_camera_from_video.py --calibration-video calibration.mp4 --pattern charuco --output outputs/calibration/camera_intrinsics.json
python main.py --path pose_video.mp4 --camera-intrinsics outputs/calibration/camera_intrinsics.json --optical-flow-pose
```

也可以提供整合模式：

```bash
python main.py --path pose_video.mp4 --calibration-video calibration.mp4 --optical-flow-pose
```

## 7. 實作順序建議

1. 先完成 calibration video 到 `camera_intrinsics.json`。
2. 再完成 pose video I/O 與 overlay writer。
3. 再完成 feature detection 與 LK flow visualization。
4. 再加入 undistort 與 resize-aware `K`。
5. 再加入 Essential Matrix + recoverPose。
6. 最後加入 smoothing、confidence、verification。

