# Camera Calibration and Intrinsics Analysis

## 1. 目的

本文件定義 Optical Flow Pose Pipeline 中 camera intrinsics 的背景知識、限制與升級路線。

目前主決策是：第一版不假設能取得 chessboard / Charuco calibration video，也不要求一般使用者手動輸入 FOV、`f_x`、`f_y`。因此主流程先使用 approximate K 做 debug-only relative pose。

第一版主流程：

```text
讀取 pose video
-> 根據影像解析度建立 approximate K
-> optical-flow pose pipeline 使用 approximate K
-> 所有輸出標記 intrinsics_not_calibrated / approximate_K_used / pose_for_debug_only
```

## 2. 為什麼不能只從一般影片可靠推出 K

一般影片中的 optical flow 只提供 2D pixel displacement：

```text
flow = (u2 - u1, v2 - v1)
```

它會同時受到下列因素影響：

- camera rotation
- camera translation
- scene depth
- dynamic objects
- rolling shutter
- lens distortion
- feature tracking noise

因此，單靠一般影片通常無法穩定、唯一地估出精確的 `c_x`、`c_y`、`f_x`、`f_y`。可以做 self-calibration 或 focal search，但這比較適合後續研究版，不適合作為第一版主要流程。

## 3. 第一版選擇：Approximate K

第一版使用 approximate K，原因是：

| 原因 | 說明 |
|---|---|
| 與目前資料條件一致 | 不假設一定能取得 calibration video |
| 使用者門檻低 | 不要求使用者理解 FOV、`f_x`、`f_y` |
| 工程啟動快 | 可以先驗證 optical flow、RANSAC、pose overlay 與 debug 流程 |
| 風險可控 | 所有輸出都標示 debug-only，不宣稱 calibrated pose |

Approximate K：

```text
f = max(width, height)
cx = width / 2
cy = height / 2
K =
| f   0  cx |
| 0   f  cy |
| 0   0   1 |
```

限制：

- 無法修正 lens distortion。
- yaw / pitch / roll 可能有系統性誤差。
- 結果只適合 debug、趨勢觀察、參數比較。

## 3.1 後續升級：Calibration Video

若未來能取得 calibration video，可以升級為 calibrated K：

```text
拍攝棋盤格或 Charuco board calibration video
-> 從影片抽取 calibration frames
-> 偵測 calibration pattern corners
-> 使用 cv2.calibrateCamera
-> 輸出 camera_intrinsics.json
-> 提供 optical-flow pose pipeline 使用
```

Calibration video 的優點：

| 原因 | 說明 |
|---|---|
| OpenCV 支援完整 | 可使用 `cv2.findChessboardCorners`、`cv2.aruco`、`cv2.calibrateCamera` |
| 結果可驗證 | 可輸出 reprojection error |
| 可估 lens distortion | 不只得到 `K`，也能得到 distortion coefficients |
| 適合正式 pose recovery | Essential Matrix / recoverPose 需要可靠 `K` |

## 4. Camera Intrinsic Matrix

`cv2.calibrateCamera` 會估出：

```text
K =
| f_x   0   c_x |
|  0   f_y  c_y |
|  0    0    1  |
```

其中：

| 參數 | 說明 |
|---|---|
| `f_x` | x 方向 pixel focal length |
| `f_y` | y 方向 pixel focal length |
| `c_x` | principal point x，通常接近影像中心 |
| `c_y` | principal point y，通常接近影像中心 |

也會得到 distortion coefficients：

```text
dist_coeffs = [k1, k2, p1, p2, k3, ...]
```

## 5. Calibration Video 輸入需求

以下內容只屬於後續 calibrated K 升級路線，不是第一版必要輸入。

| 項目 | 建議 |
|---|---|
| Pattern | Chessboard 或 Charuco board |
| 影片長度 | 10 到 30 秒即可 |
| 姿態變化 | pattern 要出現在畫面不同位置與角度 |
| 覆蓋範圍 | 左上、右上、左下、右下、中心都要出現 |
| 清晰度 | 避免 motion blur |
| 相機設定 | calibration video 與 pose video 必須使用相同解析度、焦段、鏡頭設定 |

## 6. Chessboard vs Charuco

| 方法 | 優點 | 缺點 | 第一版建議 |
|---|---|---|---|
| Chessboard | OpenCV 支援簡單、容易印製 | 必須看到足夠完整角點 | 可作第一版 |
| Charuco board | 對遮擋較容忍，corner ID 更穩 | 需要 OpenCV aruco / contrib 支援 | 推薦作進階或預設首選 |

如果環境已安裝 `opencv-contrib-python`，建議優先使用 Charuco。若只使用 `opencv-python`，先使用 Chessboard。

## 7. Calibration Output

建議輸出：

```json
{
  "image_width": 1920,
  "image_height": 1080,
  "camera_matrix": [
    [1370.2, 0.0, 960.4],
    [0.0, 1368.7, 541.1],
    [0.0, 0.0, 1.0]
  ],
  "dist_coeffs": [-0.12, 0.03, 0.001, -0.002, 0.0],
  "reprojection_error": 0.42,
  "calibration_pattern": "charuco",
  "calibration_frame_count": 38,
  "source": "calibration_video",
  "warnings": []
}
```

## 8. FOV 與 fx/fy 的角色

FOV 與 `f_x`、`f_y` 仍是有效公式，但不作為第一版主要使用者輸入。

```text
f_x = W / (2 * tan(FOV_x / 2))
f_y = H / (2 * tan(FOV_y / 2))
```

保留用途：

- 工程 fallback
- debug sanity check
- 沒有 calibration video 時的低可信度近似

若使用 fallback，輸出必須標記：

```json
{
  "source": "estimated_from_fov_or_default",
  "confidence": 0.3,
  "warnings": ["intrinsics_not_calibrated"]
}
```

## 9. 對 Optical Flow Pose 的影響

Optical flow points 需要轉成 normalized camera coordinate：

```text
x_n = (u - c_x) / f_x
y_n = (v - c_y) / f_y
```

因此 `K` 不可靠時：

- Essential Matrix 估計會偏移
- recoverPose 的 `R` 可能不穩
- yaw / pitch / roll 會出現系統性誤差
- inlier ratio 可能下降

## 10. 後續工具切入點

若要做 calibrated K 升級，可新增：

```text
tools/calibration/calibrate_camera_from_video.py
```

輸入 calibration video，輸出：

```text
outputs/calibration/camera_intrinsics.json
outputs/calibration/calibration_report.md
outputs/calibration/debug/detected_corners/
```
