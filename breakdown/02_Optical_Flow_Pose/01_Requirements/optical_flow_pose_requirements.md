# Optical Flow Pose Requirements

## Goals

1. 可讀取影片並抽樣 frame。
2. 可由 calibration video 解析 camera intrinsics：`f_x`、`f_y`、`c_x`、`c_y` 與 distortion coefficients。
3. 可計算 optical flow speed 並畫出 motion paths。
4. 可將 2D pixel flow 轉成 normalized camera coordinate。
5. 可輸出 analysis report，供後續 pose estimator 使用。

## Non-goals

- 不在第一輪做 SLAM。
- 不在第一輪做 dense 3D reconstruction。
- 不在第一輪估絕對 metric speed。
- 不在第一輪加入 deep learning optical flow。
