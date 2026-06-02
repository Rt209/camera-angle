# 2D and 3D Coordinate Transform Matrix Analysis

## 1. 目的

本文件整理 optical-flow pose pipeline 中 2D pixel、normalized camera coordinate、camera 3D ray、world/camera transform 的轉換關係。

這一輪需要把光流從「影像上的速度」提升成「相機座標下的運動線索」，所以必須先統一座標系與轉換矩陣。

第一版的 camera intrinsic matrix `K` 來源是 calibration video，也就是棋盤格或 Charuco board 搭配 `cv2.calibrateCamera`。一般使用者不需要手動輸入 FOV、`f_x` 或 `f_y`。

## 2. 座標系

| 座標系 | 符號 | 說明 |
|---|---|---|
| pixel coordinate | `(u, v)` | 影像左上角為原點 |
| normalized camera coordinate | `(x, y, 1)` | 經過 intrinsics inverse normalize |
| camera coordinate | `(X_c, Y_c, Z_c)` | 相機自身座標 |
| world coordinate | `(X_w, Y_w, Z_w)` | 外部世界座標 |

## 3. Pixel 到 Normalized Camera Coordinate

```text
p_pixel = [u, v, 1]^T
p_norm = K^-1 * p_pixel
```

展開：

```text
x = (u - c_x) / f_x
y = (v - c_y) / f_y
```

其中：

```text
p_norm = [x, y, 1]^T
```

這代表一條從 camera center 出發的 3D ray。

## 4. 3D 到 2D Projection

camera coordinate：

```text
P_c = [X_c, Y_c, Z_c]^T
```

projection：

```text
p_pixel_h = K * P_c
u = p_pixel_h.x / p_pixel_h.z
v = p_pixel_h.y / p_pixel_h.z
```

## 5. Camera Pose Transform

world 到 camera：

```text
P_c = R * P_w + t
```

homogeneous matrix：

```text
T_cw =
| R  t |
| 0  1 |
```

camera 到 world：

```text
T_wc = inverse(T_cw)
```

## 6. Optical Flow 與 Pose 的關係

兩個 frame 的同一點：

```text
p1 = [u1, v1, 1]^T
p2 = [u2, v2, 1]^T
flow = p2 - p1
```

轉 normalized：

```text
r1 = K^-1 * p1
r2 = K^-1 * p2
```

如果只看方向變化：

```text
ray_delta = r2 - r1
```

這可以作為 camera rotation / translation estimation 的輸入，但若沒有 depth，無法唯一恢復完整 3D motion。

## 7. 必須保留的不確定性

單目影片 optical flow 本身有幾個限制：

- 沒有 depth 時，translation scale 不可觀測。
- moving object 會和 camera motion 混在一起。
- pure rotation 可以用 homography/essential matrix 較好處理。
- forward motion 需要 focus of expansion 與 outlier filtering。
- `f_x`、`f_y` 錯誤會放大姿態估計誤差。

所以第一輪工具應該輸出 motion features 與 confidence，而不是假裝已經有精確 3D velocity。

## 8. 建議輸出資料結構

```json
{
  "intrinsics": {
    "fx": 721.5,
    "fy": 721.5,
    "cx": 621.0,
    "cy": 187.5
  },
  "transform_convention": "world_to_camera",
  "normalized_flow_summary": {
    "median_dx": 0.003,
    "median_dy": -0.001,
    "radial_expansion_score": 0.62
  },
  "pose_observability": {
    "rotation": "partial",
    "translation_direction": "partial",
    "translation_scale": "unobservable_without_depth"
  }
}
```

## 9. 後續工具切入點

建議新增：

```text
tools/analyze_coordinate_transforms.py
```

第一版目標：

- 讀取由 calibration video 產生的 intrinsics JSON
- 將 selected tracks 從 pixel flow 轉 normalized flow
- 輸出轉換後的 summary
- 產生座標轉換 sanity check report
