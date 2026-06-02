# Outputs

此資料夾保存已產生的影片、CSV、JSON、評估報告與 debug 圖。

## `outputs/video_pose`

Geometry-based visual pose pipeline 的輸出。

主要檔案：

```text
outputs/video_pose/predicted_pose_overlay.mp4
outputs/video_pose/pose_timeline.csv
outputs/video_pose/frame_pose_results.json
outputs/video_pose/evaluation/evaluation_report.md
outputs/video_pose/evaluation/pose_vs_oxts.csv
outputs/video_pose/evaluation/pose_vs_oxts_summary.json
outputs/video_pose/evaluation/worst_frames.csv
```

評估意義：

- 比較 geometry-based predicted yaw / pitch / roll 與 KITTI OXTS absolute yaw / pitch / roll。
- 此 pipeline 以 edges、lines、horizon、vanishing point 等幾何特徵為主。

## `outputs/optical_flow_pose/pose_overlay_uncalibrated`

Optical-flow pose debug prototype 的主要輸出，也是目前 `.gitignore` 允許上傳的 optical-flow outputs 目錄。

主要檔案：

```text
outputs/optical_flow_pose/pose_overlay_uncalibrated/output_pose_overlay.mp4
outputs/optical_flow_pose/pose_overlay_uncalibrated/pose_timeline.csv
outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json
outputs/optical_flow_pose/pose_overlay_uncalibrated/debug_frames/
outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/evaluation_report.md
outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/relative_pose_vs_oxts.csv
outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/relative_pose_vs_oxts_summary.json
outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/worst_frames.csv
```

評估意義：

- 比較 optical-flow predicted frame-to-frame relative yaw / pitch / roll 與 KITTI OXTS frame-to-frame angle delta。
- 這不是 calibrated pose result。
- 每筆結果都應保留 `intrinsics_not_calibrated`、`approximate_K_used`、`pose_for_debug_only`。

## 實驗輸出

以下目錄屬於參數實驗或中間 debug 輸出，預設不作為主要上傳內容：

```text
outputs/optical_flow_pose/sparse_flow/
outputs/optical_flow_pose/parameter_debug/
debug/experiments/optical_flow_pose/
```
