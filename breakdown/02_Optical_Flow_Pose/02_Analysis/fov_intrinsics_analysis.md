# Camera Calibration and Intrinsics Analysis

## 1. 目的

本文件定義 Optical Flow Pose Pipeline 如何取得 camera intrinsics。

新的需求假設是：一般使用者不會知道 FOV、`f_x`、`f_y` 是什麼，也不應被要求手動輸入這些參數。因此第一版不以「手動輸入 FOV / focal length」作為主要流程，而是使用 calibration video 取得 camera intrinsic matrix `K`。

第一版主流程：

```text
拍攝棋盤格或 Charuco board calibration video
-> 從影片抽取 calibration frames
-> 偵測 calibration pattern corners
-> 使用 cv2.calibrateCamera
-> 輸出 camera_intrinsics.json
-> 提供 optical-flow pose pipeline 使用
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

## 3. 第一版選擇：Calibration Video

第一版使用 calibration video，原因是：

| 原因 | 說明 |
|---|---|
| 使用者容易理解 | 使用者只需要拍棋盤格或 Charuco board，不需要理解 `f_x`、`f_y` |
| OpenCV 支援完整 | 可使用 `cv2.findChessboardCorners`、`cv2.aruco`、`cv2.calibrateCamera` |
| 結果可驗證 | 可輸出 reprojection error |
| 可估 lens distortion | 不只得到 `K`，也能得到 distortion coefficients |
| 適合後續 pose recovery | Essential Matrix / recoverPose 需要可靠 `K` |

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

第一版工具應改為：

```text
tools/calibrate_camera_from_video.py
```

輸入 calibration video，輸出：

```text
outputs/calibration/camera_intrinsics.json
outputs/calibration/calibration_report.md
outputs/calibration/debug/detected_corners/
```

