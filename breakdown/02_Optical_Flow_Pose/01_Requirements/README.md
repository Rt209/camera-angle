# Optical Flow Pose Requirements

## Evaluation Requirements

| ID | Requirement | Acceptance definition |
|---|---|---|
| ER-01 | 計算 `Precision@θ` | `correct_valid_predictions / valid_predictions` |
| ER-02 | 計算 `Recall@θ` | `correct_valid_predictions / reference_frames`；dropout 仍納入分母 |
| ER-03 | 計算 `Geodesic MAE` | 有效幀 SO(3) Geodesic Error 平均值，單位 degree |
| ER-04 | 計算 `P95 Error` | 有效幀 Geodesic Error 第 95 百分位 |
| ER-05 | 計算 `Jitter` | 連續幀 rotation-error Geodesic 變化量的 RMS |
| ER-06 | 允許設定 `θ` | 預設 `1.0°`，可使用 `--theta-deg` 覆寫 |
| ER-07 | 使用一致姿態語意 | predicted relative rotation 僅比較 OXTS frame-to-frame delta |
| ER-08 | 預設精簡輸出 | 僅輸出 `summary.json`、`per_frame.csv`、`evaluation_report.md` |

## 1. 目的

本文件定義 optical flow camera-pose estimation pipeline 的功能需求、非功能需求、輸入輸出格式與限制條件。

## 2. 功能需求

| ID | Requirement | 說明 |
|---|---|---|
| FR-01 | 讀取影片 | 支援 `.mp4`、`.avi`、`.mov` 等常見格式 |
| FR-02 | 逐幀處理 | 可取得 frame index、timestamp、fps、解析度 |
| FR-03 | 影像前處理 | 支援灰階、resize、Gaussian blur、contrast normalization |
| FR-04 | 特徵點偵測 | 第一版使用 Shi-Tomasi corner detection |
| FR-05 | Optical flow 追蹤 | 第一版使用 Pyramidal Lucas-Kanade sparse optical flow |
| FR-06 | 建立相機內參 | 使用 calibration video，透過 `cv2.calibrateCamera` 建立 `K` 與 distortion coefficients |
| FR-07 | 幾何估計 | 使用 Essential Matrix + RANSAC 估計相對幾何 |
| FR-08 | Pose recovery | 使用 `recoverPose` 或等價方法取得 `R`、`t` |
| FR-09 | Euler angles | 將 rotation matrix 轉 yaw、pitch、roll |
| FR-10 | Overlay visualization | 將 flow、tracked points、pose、inlier count、confidence 疊加到影片 |
| FR-11 | Debug output | 輸出 tracked point count、inlier count、inlier ratio、failure warnings |
| FR-12 | Pose log | 輸出 CSV / JSON pose timeline |

## 3. 非功能需求

| ID | Requirement | 說明 |
|---|---|---|
| NFR-01 | 模組化 | video I/O、tracking、geometry、pose、visualization 應分層 |
| NFR-02 | 可調參 | feature count、LK window、RANSAC threshold、calibration board size 等需可設定 |
| NFR-03 | 可重現 | 相同輸入與 config 應產生一致結果 |
| NFR-04 | 易 debug | 每個階段應能輸出中間統計與可視化 |
| NFR-05 | 支援不同解析度 | resize 時必須同步更新 intrinsics |
| NFR-06 | 可擴充驗證 | 未來可接 KITTI OXTS 或其他 ground truth |
| NFR-07 | 低依賴 | 第一版優先使用 OpenCV / NumPy |

## 4. 輸入格式

| 欄位 | 說明 |
|---|---|
| `video_path` | 要估計 pose 的影片路徑 |
| `calibration_video_path` | 相同相機與解析度拍攝的棋盤格或 Charuco board calibration video |
| `output_path` | 輸出影片路徑 |
| `calibration_pattern` | `chessboard` 或 `charuco` |
| `board_rows`, `board_cols` | calibration board 的角點或格點配置 |
| `square_size` | calibration board 每格實際尺寸，可用任意單位；若只估 rotation，可保持一致即可 |
| `camera_intrinsics_path` | 可選，若已完成 calibration，可直接讀取 JSON |
| `resize_width` | 可選，處理時的目標寬度 |
| `frame_step` | 可選，每幾幀估計一次 |

## 5. 輸出格式

### 5.1 Output Video

輸出影片應至少顯示：

- optical flow vectors
- tracked feature points
- yaw / pitch / roll
- inlier count
- inlier ratio
- confidence
- warnings，例如 `too_few_tracks`

### 5.2 Pose Log

```json
{
  "frame_index": 120,
  "timestamp_sec": 4.0,
  "yaw_deg": 1.24,
  "pitch_deg": -0.18,
  "roll_deg": 0.05,
  "tracked_points": 183,
  "inliers": 142,
  "inlier_ratio": 0.776,
  "confidence": 0.73,
  "warnings": []
}
```

## 6. 限制條件

| 限制 | 影響 |
|---|---|
| 單眼影片無法直接得到真實尺度 translation | `t` 只能視為方向，不可當作真實公尺速度 |
| 動態物體會干擾 optical flow | 可能造成 Essential Matrix 錯誤 |
| 低紋理區域可能追蹤失敗 | tracked point count 下降 |
| calibration video 品質不佳 | yaw / pitch / roll 會有系統性誤差 |
| Euler angle convention 不固定 | 不同定義會得到不同 yaw / pitch / roll |
| 純旋轉或平面場景 | Essential Matrix / Homography 適用性需要判斷 |
| motion blur | LK tracking 與 feature detection 會不穩 |

## 7. 第一版完成標準

第一版可接受：

- 以相對姿態變化為主，不輸出絕對世界姿態。
- translation 只輸出方向或不輸出 metric scale。
- yaw / pitch / roll 以 frame-to-frame relative rotation 或累積 rotation 呈現。
- 使用 inlier ratio 與 tracking quality 表示 confidence。
- 一般使用者不需要輸入 FOV、`f_x`、`f_y`；第一版由 calibration video 取得 intrinsics。
