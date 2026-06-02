# Stage 11-13: Optical Flow Pose Pipeline

## 1. 目標

建立一條新的影片姿態分析 pipeline，使用 calibration video 取得 camera intrinsics，再使用 optical flow 估計 camera motion features 與姿態變化。

此階段先以 calibration 與 analysis tools 為主，不直接替換既有 geometry-based pipeline。

## 2. Stage 切分

| Stage | 名稱 | 目標 |
|---|---|---|
| Stage 11 | Calibration Video Camera Intrinsics | 使用棋盤格或 Charuco board calibration video 建立 `K` 與 distortion coefficients |
| Stage 12 | Optical Flow Path Analyzer | 計算 flow speed 並畫出 movement paths |
| Stage 13 | Coordinate Transform and Motion Features | 2D/3D 轉換矩陣與 normalized flow analysis |

## 3. Stage 11 實作

建議新增：

```text
tools/calibrate_camera_from_video.py
src/contexts/camera_model/domain/intrinsics.py
src/contexts/camera_model/domain/calibration_result.py
src/contexts/camera_model/services/calibration_frame_sampler.py
src/contexts/camera_model/services/calibration_board_detector.py
src/contexts/camera_model/services/camera_calibrator.py
tests/test_camera_calibrator.py
```

輸入：

```text
calibration video path
calibration pattern: chessboard | charuco
board rows / cols
square size
minimum valid calibration frames
```

輸出：

```text
outputs/calibration/camera_intrinsics.json
outputs/calibration/calibration_report.md
outputs/calibration/debug/detected_corners/
```

## 4. Stage 12 實作

建議新增：

```text
tools/analyze_optical_flow_paths.py
src/contexts/motion_analysis/domain/flow_track.py
src/contexts/motion_analysis/services/sparse_flow_tracker.py
src/contexts/motion_analysis/services/flow_statistics.py
src/contexts/output/services/motion_debug_visualizer.py
tests/test_sparse_flow_tracker.py
```

輸出：

```text
outputs/optical_flow/flow_tracks.csv
outputs/optical_flow/flow_summary.json
outputs/optical_flow/debug/02_flow_vectors.png
outputs/optical_flow/debug/03_tracked_paths.png
```

## 5. Stage 13 實作

建議新增：

```text
tools/analyze_coordinate_transforms.py
src/contexts/coordinate_transform/domain/camera_transform.py
src/contexts/coordinate_transform/services/pixel_to_camera.py
src/contexts/motion_analysis/services/motion_feature_estimator.py
tests/test_coordinate_transforms.py
```

輸出：

```text
outputs/coordinate_transform/normalized_flow_summary.json
outputs/coordinate_transform/transform_report.md
```

## 6. CLI 暫定

Analysis tool 階段：

```bash
python tools/calibrate_camera_from_video.py --calibration-video calibration.mp4 --pattern charuco --output outputs/calibration/camera_intrinsics.json
python tools/analyze_optical_flow_paths.py --path examples/video.mp4 --output-dir outputs/optical_flow
python tools/analyze_coordinate_transforms.py --intrinsics outputs/calibration/camera_intrinsics.json --tracks outputs/optical_flow/flow_tracks.csv
```

正式 pipeline 階段：

```bash
python main.py --path examples/video.mp4 --camera-intrinsics outputs/calibration/camera_intrinsics.json --optical-flow-pose
```

## 7. 驗收條件

Stage 11：

- 可從 calibration video 抽取有效 calibration frames。
- 可偵測 chessboard 或 Charuco corners。
- 可輸出 `K`、distortion coefficients、reprojection error。
- 可在 pose video resize 後同步縮放 intrinsics。
- 不要求一般使用者輸入 FOV、`f_x` 或 `f_y`。

Stage 12：

- 可讀取影片並產生 sparse optical flow tracks。
- 可輸出 speed statistics。
- 可畫出 flow vectors 與 tracked paths。

Stage 13：

- 可把 pixel flow 轉 normalized flow。
- 可輸出 radial expansion / rotation flow score。
- 可說明 translation scale 在沒有 depth 時不可觀測。

## 8. 下一步

先從 `tools/calibrate_camera_from_video.py` 開始，因為 optical flow、Essential Matrix 與 2D/3D 轉換都依賴同一組可靠 intrinsics。

