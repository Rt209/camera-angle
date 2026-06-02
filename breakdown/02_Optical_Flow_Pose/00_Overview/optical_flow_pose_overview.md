# Optical Flow Pose Overview

這是新一輪 video optical-flow pose pipeline 的 overview。

這條技術路線和 geometry-based single image pipeline 分開管理，核心差異是：

- 使用連續 frame 的 optical flow，而不是單張影像幾何線索。
- 先分析 flow speed、feature tracks、motion path。
- 使用 camera intrinsics matrix `K` 將 pixel flow 轉成 normalized camera coordinate。
- 再評估 camera motion features 與姿態候選。

## First Milestone

第一個 milestone 是建立 calibration 與 analysis tools：

```text
tools/calibrate_camera_from_video.py
tools/analyze_optical_flow_paths.py
tools/analyze_coordinate_transforms.py
```
