# Breakdown Index

這個資料夾依照技術路線分類，每個分類內部各自保留 `00_Overview` 到 `06_Debug` 的 breakdown 階段。

## Breakdown Types

| Folder | Type | Description |
|---|---|---|
| `01_Geometry_Based_Pose/` | Geometry-based pose | 既有 single image geometry pipeline，使用 lines、horizon、vanishing point 估 yaw / pitch / roll。 |
| `02_Optical_Flow_Pose/` | Optical-flow pose | 新一輪 video optical flow pipeline，使用 flow speed、tracks、camera intrinsics、2D/3D transform 分析影片姿態。 |

