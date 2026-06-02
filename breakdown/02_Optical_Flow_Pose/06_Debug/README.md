# Optical Flow Pose Debug

## 1. 目的

本章節只針對 optical-flow pose prototype 的 debug 文件、實驗設計與代表性 artifacts。

目前專案不再假設會取得 calibration video，因此 debug 重點不是 camera calibration，而是：

- sparse optical flow tracking 是否穩定
- Essential Matrix / RANSAC 是否受 outlier 或退化幾何影響
- approximate K 對 pitch / roll outlier 的敏感度
- confidence 是否能辨識錯誤 frame

## 2. Debug 類別

| 類別 | 可能原因 | 建議檢查 |
|---|---|---|
| tracking failure | motion blur、低紋理、特徵點離開畫面 | LK status、LK error、tracked point count |
| too few feature points | 畫面紋理不足、quality threshold 過高 | Shi-Tomasi output、feature distribution |
| too few RANSAC inliers | 動態物體、錯誤 tracking、RANSAC threshold 太嚴 | inlier mask、flow overlay |
| high-inlier wrong pose | approximate K 不準、recoverPose ambiguity、場景幾何退化 | outlier frame deep dive、K sensitivity、RANSAC sweep |
| unstable Euler angles | rotation order 錯、R matrix 不穩、gimbal lock 附近 | R matrix、angle delta、yaw/pitch/roll timeline |
| moving object interference | 車、人、物體佔據大量 flow | inlier/outlier overlay |
| low texture scene | 天空、暗處、遠方平面過多 | feature spatial distribution |
| confidence mismatch | 高 confidence 但角度錯 | high-confidence-high-error frame、unreliable warning recall |
| video writer codec issue | codec 不支援或 frame size 不一致 | fps、fourcc、frame size |
| coordinate system mismatch | camera/world convention 不一致 | sign test、relative OXTS delta comparison |

## 3. Debug Artifacts

```text
debug/experiments/optical_flow_pose/
  001_baseline/
    params/config.json
    metrics/relative_pose_vs_oxts_summary.json
    reports/baseline_report.md
  005_outlier_frame_deep_dive/
    params/config.json
    metrics/outlier_frames.json
    metrics/frame_000079.json
    frames/frame_000079_input.png
    frames/frame_000079_flow_vectors.png
    frames/frame_000079_inliers_outliers.png
    frames/frame_000079_pose_overlay.png
    reports/experiment_report.md
```

正式整理報告放在：

```text
outputs/optical_flow_pose/parameter_debug/evaluation_report.md
```

## 4. Debug 指令

```powershell
python tools/debug_optical_flow_pose_parameters.py ^
  --video tools/output/kitti_no_overlay.mp4 ^
  --oxts-dir tools/input/oxts ^
  --output-root outputs/optical_flow_pose/parameter_debug ^
  --debug-root debug/experiments/optical_flow_pose ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```

## 5. Debug 原則

- 只比較 optical-flow predicted frame-to-frame relative rotation 與 OXTS frame-to-frame delta。
- 不比較 OXTS absolute yaw / pitch / roll。
- 所有 pose result 必須保留 `intrinsics_not_calibrated`、`approximate_K_used`、`pose_for_debug_only`。
- 若 pose 不可信，overlay 與 JSON 應明確標示 warning。
- 若要進一步調參，先看 outlier frame deep dive，再決定做 approximate K sensitivity、RANSAC sweep 或 confidence calibration。
