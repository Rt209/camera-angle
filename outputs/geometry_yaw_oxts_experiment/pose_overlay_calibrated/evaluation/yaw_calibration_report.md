# Geometry Yaw Calibration Transform Report

## 目的

本實驗建立 `calibration transform -> calibrated_heading_yaw`，避免繼續把 `image_geometry_yaw` 直接拿去和 KITTI OXTS absolute heading 比較。

## Calibration Model

| Field | Value |
|---|---:|
| model type | linear |
| scale | -0.270509 |
| yaw offset | -55.564465 deg |
| calibration segment | frame 0-80 |
| validation segment | frame 81-153 |

候選模型比較：

| Model | Calibration MAE | Validation MAE | All MAE |
|---|---:|---:|---:|
| offset-only | 23.8186 | 51.3747 | 36.8809 |
| linear | 11.9392 | 30.8956 | 20.9250 |

## Before / After

| Segment | Before | After |
|---|---:|---:|
| All frames | 34.3517 deg | 20.9250 deg |
| Calibration 0-80 | 24.8485 deg | 11.9392 deg |
| Validation 81-153 | 44.8963 deg | 30.8956 deg |
| Frame 91-100 | 7.0835 deg | 16.5434 deg |
| Frame 112-117 | 75.2228 deg | 28.7129 deg |
| Frame 150-153 | 70.9991 deg | 31.5733 deg |

Confidence failure:

```text
before = 17
after  = 0
```

## 圖表

![Calibrated yaw predicted vs OXTS](calibrated_yaw_pred_vs_oxts.png)

![Raw vs calibrated yaw error](raw_vs_calibrated_yaw_error.png)

![Calibrated confidence vs absolute error](calibrated_confidence_vs_abs_error.png)

## 驗收

```text
validation_mae_improved = True
confidence_failure_reduced = True
frame_112_117_improved = True
frame_150_153_improved = True
status = success
```

## 解讀

此實驗沒有針對特定 frame 寫 rule，而是只使用 frame 0-80 學習 transform 參數，再在 frame 81-153 驗證。若 validation MAE 下降，代表 image-geometry yaw 與 OXTS heading 至少存在可用的一階線性校準關係。

需要注意：這仍是資料驅動的 yaw calibration，不等同於完整 camera-to-vehicle extrinsic calibration。若要進一步治本，下一步應建立明確的 camera intrinsics / extrinsics 與世界座標轉換。
