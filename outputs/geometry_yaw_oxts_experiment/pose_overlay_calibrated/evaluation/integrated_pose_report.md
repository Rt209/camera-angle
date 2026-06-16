# Integrated Geometry Pose Evaluation

本報告把 geometry yaw calibration 實驗的 yaw、pitch、roll 數據整合在同一份 evaluation 中。

## 資料來源

```text
Current pitch / roll / reliability-gated yaw:
outputs/video_pose/evaluation/pose_vs_oxts.csv

Calibrated yaw:
outputs/geometry_yaw_oxts_experiment/evaluation/calibrated_pose_vs_oxts.csv

Integrated output:
outputs/geometry_yaw_oxts_experiment/evaluation/integrated_pose_vs_oxts.csv
```

## 整體指標

| Metric | Value |
|---|---:|
| Rows | 154 |
| Yaw MAE current | 34.3517 deg |
| Yaw MAE calibrated | 20.9250 deg |
| Pitch MAE | 1.3891 deg |
| Roll MAE | 1.5228 deg |
| Yaw RMSE current | 40.3713 deg |
| Yaw RMSE calibrated | 26.2045 deg |
| Pitch RMSE | 1.8433 deg |
| Roll RMSE | 1.9023 deg |
| Confidence failure before | 17 |
| Confidence failure after | 0 |

## Segment 指標

| Segment | Yaw Current MAE | Yaw Calibrated MAE | Pitch MAE | Roll MAE | Failure Before | Failure After |
|---|---:|---:|---:|---:|---:|---:|
| Calibration 0-80 | 24.8485 | 11.9392 | 1.3665 | 1.7627 | 0 | 0 |
| Validation 81-153 | 44.8963 | 30.8956 | 1.4142 | 1.2566 | 17 | 0 |
| Frame 91-100 | 7.0835 | 16.5434 | 1.8869 | 0.5729 | 0 | 0 |
| Frame 112-117 | 75.2228 | 28.7129 | 1.4904 | 1.7415 | 3 | 0 |
| Frame 150-153 | 70.9991 | 31.5733 | 0.4884 | 1.4362 | 2 | 0 |

## Worst Frames

### Calibrated Yaw

```text
frame 131: pred=-42.9127, oxts=-96.9192, abs_error=54.0065, confidence=0.84
frame 130: pred=-42.9073, oxts=-96.7621, abs_error=53.8548, confidence=0.83
frame 132: pred=-43.1968, oxts=-96.9032, abs_error=53.7064, confidence=0.81
frame 133: pred=-43.1616, oxts=-96.7375, abs_error=53.5759, confidence=0.83
frame 134: pred=-43.0182, oxts=-96.4058, abs_error=53.3876, confidence=0.83
```

### Pitch

```text
frame 117: pred=-4.6800, oxts=0.5749, abs_error=5.2549, confidence=0.88
frame 138: pred=-3.5800, oxts=1.2984, abs_error=4.8784, confidence=0.86
frame 119: pred=-4.2800, oxts=0.4827, abs_error=4.7627, confidence=0.86
frame 121: pred=-4.2700, oxts=0.4633, abs_error=4.7333, confidence=0.78
frame 88: pred=4.7700, oxts=0.0455, abs_error=4.7245, confidence=0.69
```

### Roll

```text
frame 123: pred=4.1800, oxts=-1.0353, abs_error=5.2153, confidence=0.90
frame 121: pred=3.6800, oxts=-1.1342, abs_error=4.8142, confidence=0.78
frame 41: pred=-2.4900, oxts=1.9747, abs_error=4.4647, confidence=0.64
frame 16: pred=-3.2400, oxts=1.1163, abs_error=4.3563, confidence=0.61
frame 119: pred=3.1300, oxts=-1.0964, abs_error=4.2264, confidence=0.86
```

## 解讀

- Calibrated yaw MAE 比 current yaw MAE 低，代表 calibration transform 對 yaw 有整體改善。
- Pitch 與 roll 沒有套用 calibration transform，這裡保留原本 geometry pipeline 的數據，用來確認 yaw calibration 沒有混淆其他角度。
- Confidence failure 從 before 到 after 的變化，可用來檢查高 confidence 但高 yaw error 的問題是否下降。
- Frame 91-100 是 reliability gate 已改善的區段；frame 112-117 與 150-153 是 calibration transform 主要改善的區段。
