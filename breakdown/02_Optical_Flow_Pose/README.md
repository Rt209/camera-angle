# Optical Flow Pose Breakdown

這個資料夾保存以影片 optical flow 為核心的 pose debug/prototype breakdown。

它和既有 `breakdown/01_Geometry_Based_Pose/` 的 geometry-based single image pipeline 分開管理，避免把不同技術路線混在同一組階段文件裡。

## 目前決策

此專案之後不再假設會取得 chessboard / Charuco calibration video，因此 optical-flow pose 主流程固定採用 approximate K：

```text
f = max(width, height)
cx = width / 2
cy = height / 2
```

所有 optical-flow pose 結果都必須標示：

```text
intrinsics_not_calibrated
approximate_K_used
pose_for_debug_only
```

這條線只評估 frame-to-frame relative yaw / pitch / roll，不宣稱是正式 calibrated pose，也不與 OXTS absolute yaw / pitch / roll 直接比較。

## 文件順序

1. `02_Analysis/optical_flow_motion_path_analysis.md`
   - optical flow speed、feature tracks、路徑視覺化。
2. `02_Analysis/coordinate_transform_matrix_analysis.md`
   - pixel coordinate、normalized camera coordinate、approximate K 對 pose 的影響。
3. `02_Analysis/fov_intrinsics_analysis.md`
   - 保留 intrinsics 背景知識，但 calibration video 不再是主流程。
4. `03_Design/optical_flow_pose_pipeline_design.md`
   - optical-flow pose pipeline 設計與 approximate-K fallback policy。
5. `04_Implementation/stage_11_13_optical_flow_pose_pipeline.md`
   - 實作 roadmap。實際目前以 sparse flow、uncalibrated pose overlay、evaluation、parameter debug 為主。
6. `06_Debug/pose_estimation_experiment_design.md`
   - optical-only 參數 debug 實驗設計。
7. `06_Debug/optical_flow_parameter_debug_prompt.md`
   - 可交給 coding agent 執行的參數修正 prompt。

## 建議進入點

目前先從 sparse optical flow 與 uncalibrated pose overlay 開始：

```powershell
python tools/optical_flow/analyze_optical_flow_paths.py ^
  --video data/samples/kitti/videos/kitti_no_overlay.mp4 ^
  --debug-dir outputs/optical_flow_pose/sparse_flow ^
  --frame-step 1 ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```

```powershell
python tools/optical_flow/write_uncalibrated_pose_overlay.py ^
  --video data/samples/kitti/videos/kitti_no_overlay.mp4 ^
  --debug-dir outputs/optical_flow_pose/pose_overlay_uncalibrated ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```

```powershell
python tools/evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py ^
  --pose-json outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json ^
  --oxts-dir data/samples/kitti/references/oxts ^

```

若要分析 outlier 與後續調參：

```powershell
python tools/optical_flow/debug_optical_flow_pose_parameters.py ^
  --video data/samples/kitti/videos/kitti_no_overlay.mp4 ^
  --oxts-dir data/samples/kitti/references/oxts ^
  --output-root outputs/optical_flow_pose/parameter_debug ^
  --debug-root debug/experiments/optical_flow_pose ^
  --max-debug-frames 120 ^
  --output-debug-every-n-frames 10
```
