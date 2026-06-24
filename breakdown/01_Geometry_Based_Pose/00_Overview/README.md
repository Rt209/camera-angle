# Geometry Based Pose Overview

## Pose Evaluation Metrics

本專案使用 `Precision@θ`、`Recall@θ`、`Geodesic MAE`、`P95 Error` 與 `Jitter` 評估 geometry pose，預設門檻為 `θ = 3.0°`。

- `Precision@θ`：有效姿態中，Geodesic Error 不超過 `θ` 的比例。
- `Recall@θ`：全部參考影像／影片幀中，成功輸出且誤差不超過 `θ` 的比例。
- `Geodesic MAE`：SO(3) 最短旋轉角誤差的平均值。
- `P95 Error`：95% 有效姿態不超過的 Geodesic Error。
- `Jitter`：geometry video 相鄰幀 rotation-error 變化量的 RMS；單張影像為 N/A。

Raw vanishing-point yaw 是 image geometry yaw，不等於 OXTS absolute heading。未具備 calibrated heading 與 `comparison_ready=true` 時，整體 pose metrics 只能視為 diagnostic，不可宣稱 absolute heading accuracy。

這是 single-image geometry-based pose pipeline 的 overview。

這條技術路線和 `breakdown/02_Optical_Flow_Pose/` 分開管理，核心差異是：

- 使用單張影像中的幾何線索，而不是連續 frame 的 optical flow。
- 先分析 edges、line segments、horizon、vanishing point、vertical lines。
- 使用近似 camera model / FOV fallback 支援 pitch 與 yaw 的幾何估計。
- 輸出 yaw / pitch / roll、confidence 與 debug artifacts。

目前主決策：

```text
input = single image
features = edges + lines + horizon + vanishing point + vertical lines
pose = yaw + pitch + roll
output = JSON / Rich Table / debug images
```

第一版不宣稱精準 calibrated pose。若缺少可靠 camera intrinsics，yaw / pitch 只能作近似估計，輸出必須保留 method、features_used、confidence 與 warning。

## First Milestone

第一個 milestone 是建立可解釋的 geometry baseline：

```text
image loading
-> preprocessing
-> edge detection
-> line detection
-> roll estimation
-> debug artifacts
```

後續再加入：

```text
horizon detection
-> pitch estimation
-> vanishing point detection
-> yaw estimation
-> confidence scoring
-> validation
```

## 文件入口

| 階段 | 文件 | 目的 |
|---|---|---|
| Overview | `00_Overview/README.md` | 說明 geometry-based pose 主線 |
| Requirements | `01_Requirements/README.md` | 定義輸入、輸出、功能與限制 |
| Analysis | `02_Analysis/README.md` | 定義模組、資料流、工具與技術取捨 |
| Design | `03_Design/` | 定義系統模組與 bounded context |
| Implementation | `04_Implementation/` | 定義 Stage 0-10 實作順序 |
| Verification | `05_Verification/` | 定義 metrics 與驗收方式 |
| Debug | `06_Debug/` | 保存 debug process 與 artifacts |

## 與 Optical Flow Pose 的關係

| Geometry Based Pose | Optical Flow Pose |
|---|---|
| single image | video frame sequence |
| edges / lines / horizon / VP | feature tracks / optical flow |
| yaw / pitch / roll from geometry cues | relative pose from correspondences |
| debug images | debug frames / overlay video |
| first milestone: roll | first milestone: sparse flow |
