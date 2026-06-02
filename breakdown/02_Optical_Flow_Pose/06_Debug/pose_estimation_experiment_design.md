# Optical-Flow Pose Debug 實驗設計

## 1. 目標

本次 debug **只針對 optical-flow pose prototype**。

不處理 geometry-based pipeline，不調整 vanishing point、horizon、line detection，也不比較 geometry yaw / pitch / roll。

目前 optical-flow pipeline 狀態：

```text
input video:
tools/output/kitti_no_overlay.mp4

prototype output:
outputs/optical_flow_pose/pose_overlay_uncalibrated/

evaluation report:
outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/evaluation_report.md
```

目前仍是 uncalibrated debug prototype，使用 approximate K：

```text
fx = fy = max(width, height)
cx = width / 2
cy = height / 2
```

因此每一筆結果都必須保留：

```text
intrinsics_not_calibrated
approximate_K_used
pose_for_debug_only
```

## 2. 目前痛點

根據目前 optical-flow evaluation：

```text
comparison: predicted frame-to-frame relative rotation vs OXTS frame-to-frame delta
total_rows: 119
mean_inlier_ratio: 0.5472
mean_confidence: 0.1769
mean_abs_yaw_error: 0.9668 deg
mean_abs_pitch_error: 1.6467 deg
mean_abs_roll_error: 0.3920 deg
rmse_yaw_error: 1.0794 deg
rmse_pitch_error: 2.6577 deg
rmse_roll_error: 1.5497 deg
```

觀察：

- Relative yaw 平均誤差約 `0.97 deg`，目前可以當作較穩定的方向。
- Pitch 平均誤差約 `1.65 deg`，但有多個 outlier，最大約 `8.89 deg`。
- Roll 平均誤差約 `0.39 deg`，但 frame 117 有明顯 outlier，最大約 `15.30 deg`。
- Confidence 平均只有 `0.1769`，原因是 approximate K 的 intrinsics quality 被刻意壓低。
- 高 inlier ratio 不一定代表 pitch / roll 正確，代表目前 confidence 還需要重新校準。

## 3. Debug 儲存規範

所有調參過程、中間圖片、參數 JSON、臨時報告都放在：

```text
debug/experiments/optical_flow_pose/
```

建議結構：

```text
debug/experiments/optical_flow_pose/
  001_baseline/
    params/
    metrics/
    frames/
    reports/
  002_lk_feature_sweep/
    params/
    metrics/
    frames/
    reports/
  003_ransac_threshold_sweep/
    params/
    metrics/
    frames/
    reports/
  004_approx_k_sensitivity/
    params/
    metrics/
    frames/
    reports/
  005_confidence_calibration/
    params/
    metrics/
    frames/
    reports/
```

每組實驗至少保存：

```text
params/config.json
metrics/relative_pose_vs_oxts_summary.json
metrics/relative_pose_vs_oxts.csv
reports/experiment_report.md
```

若有圖片，保存：

```text
frames/frame_000079_flow_vectors.png
frames/frame_000079_inliers_outliers.png
frames/frame_000079_pose_overlay.png
frames/frame_000117_flow_vectors.png
frames/frame_000117_inliers_outliers.png
frames/frame_000117_pose_overlay.png
```

## 4. Baseline

### 4.1 目的

建立目前 optical-flow prototype 的固定基準，後續每組參數都跟 baseline 比較。

### 4.2 指令

```bash
python tools/analyze_optical_flow_paths.py ^
  --video tools/output/kitti_no_overlay.mp4 ^
  --debug-dir outputs/optical_flow_pose/sparse_flow ^
  --frame-step 1 ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```

```bash
python tools/write_uncalibrated_pose_overlay.py ^
  --video tools/output/kitti_no_overlay.mp4 ^
  --debug-dir outputs/optical_flow_pose/pose_overlay_uncalibrated ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```

```bash
python tools/evaluate_uncalibrated_pose_overlay_against_oxts.py ^
  --pose-json outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json ^
  --oxts-dir tools/input/oxts ^
  --output-dir outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation
```

### 4.3 Baseline metrics

保存到：

```text
debug/experiments/optical_flow_pose/001_baseline/metrics/
```

需要紀錄：

```text
mean_abs_yaw_error
mean_abs_pitch_error
mean_abs_roll_error
rmse_yaw_error
rmse_pitch_error
rmse_roll_error
max_abs_pitch_error
max_abs_roll_error
mean_inlier_ratio
mean_confidence
low_inlier_frame_count
high_confidence_high_error_count
```

## 5. 實驗 A：Shi-Tomasi / LK Tracking Sweep

### 5.1 假設

Pitch / roll outlier 可能來自特徵點分布不均、LK window 不適合、或追蹤點集中在局部區域。

### 5.2 參數候選

Shi-Tomasi：

```json
{
  "max_corners": [500, 1000, 1500],
  "quality_level": [0.005, 0.01, 0.02],
  "min_distance": [6, 8, 12]
}
```

Lucas-Kanade：

```json
{
  "lk_win_size": [15, 21, 31],
  "lk_max_level": [2, 3, 4],
  "lk_criteria_count": [20, 30],
  "lk_criteria_eps": [0.01]
}
```

### 5.3 優先觀察 frame

Pitch outlier：

```text
34, 38, 73, 76, 77, 79, 80
```

Roll outlier：

```text
117, 118, 119
```

### 5.4 評估指標

```text
mean_abs_yaw_error
mean_abs_pitch_error
mean_abs_roll_error
max_abs_pitch_error
max_abs_roll_error
mean_inlier_ratio
valid_track_count_mean
valid_track_count_min
```

### 5.5 成功條件

```text
mean_abs_yaw_error <= baseline + 0.2 deg
mean_abs_pitch_error 改善至少 10%
max_abs_pitch_error 改善至少 20%
max_abs_roll_error 改善至少 20%
mean_inlier_ratio >= 0.5
```

## 6. 實驗 B：Essential Matrix RANSAC Sweep

### 6.1 假設

Outlier 可能來自 RANSAC threshold 太寬或太窄，導致 recoverPose 接收錯誤 correspondences。

### 6.2 參數候選

```json
{
  "ransac_threshold": [0.5, 0.75, 1.0, 1.5, 2.0],
  "ransac_probability": [0.999],
  "min_points": [8, 20, 50]
}
```

### 6.3 評估指標

```text
mean_inlier_ratio
mean_abs_yaw_error
mean_abs_pitch_error
mean_abs_roll_error
max_abs_pitch_error
max_abs_roll_error
too_few_pose_inliers_count
```

### 6.4 成功條件

```text
mean_abs_pitch_error 改善至少 10%
max_abs_roll_error 改善至少 20%
too_few_pose_inliers_count 不高於 baseline
```

## 7. 實驗 C：Approximate K Sensitivity

### 7.1 假設

目前沒有 calibration video，因此 approximate K 可能導致 pitch / roll 對 focal length 敏感。

### 7.2 參數候選

```json
{
  "focal_scale": [0.7, 0.8, 1.0, 1.2, 1.5],
  "cx_offset_ratio": [-0.02, 0.0, 0.02],
  "cy_offset_ratio": [-0.02, 0.0, 0.02]
}
```

K 公式：

```text
f = max(width, height) * focal_scale
cx = width / 2 + width * cx_offset_ratio
cy = height / 2 + height * cy_offset_ratio
```

### 7.3 評估指標

```text
mean_abs_yaw_error
mean_abs_pitch_error
mean_abs_roll_error
max_abs_pitch_error
max_abs_roll_error
```

### 7.4 成功條件

```text
找到一組 approximate K，使 pitch / roll outlier 明顯下降
但結果仍必須標示 approximate_K_used
```

## 8. 實驗 D：Confidence Calibration

### 8.1 假設

目前 confidence 太低且不完全反映錯誤。需要將 inlier ratio、track count、pose stability、angle jump 納入。

### 8.2 候選因素

```text
inlier_ratio
valid_track_count
median_flow_magnitude
angle_delta_stability
translation_direction_stability
pose_outlier_penalty
intrinsics_quality
```

### 8.3 指標

```text
confidence_vs_abs_error_correlation
high_confidence_high_error_count
low_confidence_low_error_count
mean_confidence
unreliable_warning_precision
unreliable_warning_recall
```

建議定義：

```text
high_confidence_high_error:
  confidence >= 0.3 and max(abs_yaw_error, abs_pitch_error, abs_roll_error) >= 3 deg

unreliable:
  max(abs_yaw_error, abs_pitch_error, abs_roll_error) >= 3 deg
```

### 8.4 成功條件

```text
high_confidence_high_error_count 降低至少 30%
unreliable_warning_recall >= 0.7
mean_confidence 不低於 baseline 太多
```

## 9. 實驗 E：Outlier Frame Deep Dive

### 9.1 目的

針對 pitch / roll outlier 保存足夠影像與統計，判斷原因是 tracking、RANSAC、approx K 或 recoverPose ambiguity。

### 9.2 必看 frame

```text
34, 38, 76, 77, 79, 80, 117, 118, 119
```

### 9.3 每幀保存

```text
input frame
tracked points
flow vectors
RANSAC inliers / outliers
pose overlay
per-frame JSON:
  tracked_point_count
  inlier_count
  inlier_ratio
  yaw/pitch/roll
  OXTS delta yaw/pitch/roll
  abs errors
  warnings
```

### 9.4 判斷規則

```text
若 valid_track_count 低:
  優先調 Shi-Tomasi / LK

若 valid_track_count 高但 inlier_ratio 低:
  優先調 RANSAC threshold

若 inlier_ratio 高但 pitch/roll error 高:
  檢查 approximate K sensitivity 或 recoverPose ambiguity

若 angle 突然跳動:
  增加 temporal stability / smoothing / unreliable warning
```

## 10. 建議實驗順序

```text
1. 001_baseline
2. 005_outlier_frame_deep_dive
3. 002_lk_feature_sweep
4. 003_ransac_threshold_sweep
5. 004_approx_k_sensitivity
6. 006_confidence_calibration
```

原因：

- 先看 outlier frame，避免盲目 sweep。
- LK / feature sweep 會影響所有後續 pose。
- RANSAC threshold 是 Essential Matrix 的主要穩定參數。
- Approx K sensitivity 可判斷目前是否受未校正內參主導。
- Confidence calibration 最後做，避免基礎 pose 還在變動時重複調整。

## 11. 必跑測試

每次修改程式後：

```bash
pytest tests/test_sparse_flow_tracker.py
pytest tests/test_euler_angle_converter.py
pytest tests/test_essential_pose_estimator.py
pytest tests/test_uncalibrated_pose_overlay_pipeline.py
pytest tests/test_evaluate_uncalibrated_pose_overlay_against_oxts.py
```

若修改 calibration 相關程式：

```bash
pytest tests/test_camera_calibrator.py
```

## 12. 最終輸出

每次調參完成後，正式結果輸出到：

```text
outputs/optical_flow_pose/pose_overlay_uncalibrated/
```

實驗過程保留在：

```text
debug/experiments/optical_flow_pose/
```

最終報告需包含：

```text
最佳參數組
baseline vs best metrics
改善百分比
失敗 frame 分析
是否仍需要 calibration video
下一步建議
```

