# Optical Flow Pose Overview

這是 video optical-flow pose pipeline 的 overview。

這條技術路線和 geometry-based single image pipeline 分開管理，核心差異是：

- 使用連續 frame 的 optical flow，而不是單張影像幾何線索。
- 先分析 flow speed、feature tracks、motion path。
- 使用 approximate camera intrinsics matrix `K` 將 pixel correspondences 提供給 Essential Matrix / recoverPose。
- 輸出 frame-to-frame relative yaw / pitch / roll，只作 debug 與趨勢觀察。

目前主決策：

```text
f = max(width, height)
cx = width / 2
cy = height / 2
```

所有 pose 結果都必須標示：

```text
intrinsics_not_calibrated
approximate_K_used
pose_for_debug_only
```

## First Milestone

第一個 milestone 是建立 sparse flow、uncalibrated pose overlay 與參數 debug tools：

```text
tools/optical_flow/analyze_optical_flow_paths.py
tools/optical_flow/write_uncalibrated_pose_overlay.py
tools/evaluation/evaluate_uncalibrated_pose_overlay_against_oxts.py
tools/optical_flow/debug_optical_flow_pose_parameters.py
```

若未來取得可靠 calibration video 或 camera intrinsics file，可以把 intrinsics provider 升級成 calibrated K，但第一版不把它列為必要條件。
