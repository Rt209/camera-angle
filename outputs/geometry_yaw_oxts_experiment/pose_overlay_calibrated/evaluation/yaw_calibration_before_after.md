# Yaw Calibration Before / After

| Metric | Before | After |
|---|---:|---:|
| All yaw MAE | 34.3517 deg | 20.9250 deg |
| Calibration segment yaw MAE | 24.8485 deg | 11.9392 deg |
| Validation segment yaw MAE | 44.8963 deg | 30.8956 deg |
| Frame 91-100 yaw MAE | 7.0835 deg | 16.5434 deg |
| Frame 112-117 yaw MAE | 75.2228 deg | 28.7129 deg |
| Frame 150-153 yaw MAE | 70.9991 deg | 31.5733 deg |
| Confidence failure count | 17 | 0 |

Selected model: `linear`

```text
scale = -0.2705094869167766
yaw_offset = -55.56446532378772
calibration segment = frame 0-80
validation segment = frame 81-153
```
