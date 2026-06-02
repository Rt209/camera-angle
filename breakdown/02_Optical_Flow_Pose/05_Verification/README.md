# Optical Flow Pose Verification

## 1. 目的

本文件定義 optical flow camera-pose pipeline 的驗證方式、測試案例、指標、誤差評估與結果判讀。

## 2. 驗證目標

| 驗證項目 | 目標 |
|---|---|
| Camera calibration | 確認 calibration video 可產生可靠 `K`、distortion coefficients、reprojection error |
| Optical flow tracking | 確認 tracking points 數量、方向與畫面運動一致 |
| Essential Matrix | 確認 RANSAC inliers 足夠且 epipolar geometry 合理 |
| Pose recovery | 確認 yaw / pitch / roll 不爆值且方向合理 |
| Confidence | 確認 inlier ratio 可反映結果可信度 |
| Output video | 確認 overlay 資訊清楚且同步 |
| Ground truth comparison | 若有 KITTI OXTS，計算 MAE / RMSE |

## 3. Required Metrics

| 指標 | 說明 | 判讀 |
|---|---|---|
| tracked points | LK 成功追蹤的點數 | 太少代表 tracking failure |
| inliers | RANSAC inlier 數量 | 太少代表幾何估計不可信 |
| inlier ratio | `inliers / tracked_points` | 可作 confidence 核心 |
| mean optical flow magnitude | 平均 flow 長度 | 靜止影片應接近 0 |
| yaw / pitch / roll smoothness | frame-to-frame angle delta | 過大跳動代表不穩 |
| rotation angle magnitude | `acos((trace(R)-1)/2)` | 可偵測異常旋轉 |
| failure frame count | 無法估 pose 的幀數 | 衡量 pipeline 穩定性 |
| MAE / RMSE | 與 ground truth 比較 | 有 KITTI OXTS 時使用 |
| calibration reprojection error | calibration corner 重投影誤差 | 越低越好，過高代表 calibration 不可靠 |
| valid calibration frames | 成功偵測 board 的 frames | 太少代表 calibration 覆蓋不足 |

## 3.1 Calibration Verification

確認 camera calibration 正常：

- calibration video 與 pose video 必須使用同一台相機、同一解析度、同一焦段。
- board corners 必須覆蓋畫面中心與四周。
- valid calibration frames 不應太少，第一版建議至少 20 張。
- reprojection error 應記錄在 `calibration_report.md`。
- undistort 後的影像不應出現明顯裁切錯誤或變形。

若 calibration 不可靠，pose pipeline 應標記：

```text
intrinsics_unreliable
```

## 4. Tracking Verification

確認 optical flow tracking 正常：

- flow arrows 應沿著畫面中可追蹤背景特徵移動。
- tracked points 不應大量集中在動態物體。
- 靜止影片中 flow magnitude 應接近 0。
- 快速移動時，LK status failure 不應大幅失控。
- 低紋理畫面應觸發 `too_few_feature_points` warning。

## 5. Essential Matrix Verification

確認 Essential Matrix 合理：

```text
inlier_ratio = inlier_count / tracked_point_count
```

建議判讀：

| 條件 | 判讀 |
|---|---|
| `tracked_points < 30` | 不應估 pose |
| `inliers < 20` | pose unreliable |
| `inlier_ratio < 0.3` | 幾何模型可能錯 |
| `inlier_ratio > 0.6` | 通常較可信 |

若 Homography inlier ratio 明顯高於 Essential Matrix，應標記：

```text
planar_scene_or_pure_rotation_possible
```

## 6. Pose Verification

確認 yaw / pitch / roll 沒有爆掉：

- frame-to-frame delta 不應出現大量不合理尖峰。
- 靜止影片中 yaw / pitch / roll 應接近 0。
- pure yaw 測試中，主要變化應集中在 yaw。
- camera roll 測試中，roll 方向應符合定義。
- pitch 測試中，pitch 變化應平滑。

Rotation angle magnitude：

```text
theta = acos((trace(R) - 1) / 2)
```

若 `theta` 在相鄰幀突然過大，應降低 confidence 或標記 warning。

## 7. Ground Truth Comparison

若使用 KITTI OXTS 或其他 ground truth：

```text
error_yaw = predicted_yaw - gt_yaw
error_pitch = predicted_pitch - gt_pitch
error_roll = predicted_roll - gt_roll
MAE = mean(abs(error))
RMSE = sqrt(mean(error^2))
```

注意：

- KITTI OXTS 是世界座標 / 車體座標資料，必須先確認座標系。
- 本 pipeline 第一版多半輸出 relative pose，需要和 ground truth relative delta 比較。
- Euler angle rotation order 必須一致。

## 8. Qualitative Verification

沒有 ground truth 時，使用定性檢查：

| 場景 | 期待結果 |
|---|---|
| 畫面往右轉 | yaw 變化方向合理 |
| 相機左右傾斜 | roll 跟著變化 |
| 相機上下俯仰 | pitch 跟著變化 |
| 靜止影片 | yaw / pitch / roll 接近 0 |
| 背景為主的影片 | 光流箭頭大多落在背景特徵 |
| 動態物體穿越 | RANSAC 應排除多數 moving object points |

## 9. Failure Case Report

每個 failure frame 建議記錄：

```json
{
  "frame_index": 150,
  "reason": "too_few_ransac_inliers",
  "tracked_points": 42,
  "inliers": 8,
  "inlier_ratio": 0.19,
  "mean_flow_magnitude": 4.8,
  "warnings": ["pose_unreliable"]
}
```
