# Breakdown Index

這個資料夾依照技術路線分類，每個分類內部各自保留 `00_Overview` 到 `06_Debug` 的 breakdown 階段。

## Breakdown Types

| Folder | Type | Description |
|---|---|---|
| `01_Geometry_Based_Pose/` | Geometry-based pose | 既有 single image geometry pipeline，使用 lines、horizon、vanishing point 估 yaw / pitch / roll。 |
| `02_Optical_Flow_Pose/` | Optical-flow pose | 新一輪 video optical flow pipeline，使用 flow speed、tracks、camera intrinsics、2D/3D transform 分析影片姿態。 |
| `03_Interactive_CLI/` | Interactive CLI | 使用單一啟動指令，以 InquirerPy 與 Rich 引導使用者完成輸入、模式、輸出及執行設定。 |
# Phase 1 implementation status

The shared input/output contract, run-directory naming, sample migration, pipeline metadata, frame identity, evaluation artifact naming, and migration of reference-based Evaluation services into `src` are implemented. Interactive CLI, `RunPlanDraft`/`RunPlan`, and Pose Quality Diagnostics are explicitly remaining work.

Standalone Evaluation defaults use `outputs/<run_id>/eval/geometry` and `outputs/<run_id>/eval/optical`; `--output-dir` remains a supported override. The formal rotation contract is fixed to ZYX degrees.

Repository-managed run IDs use `YYYYMMDD_HHMMSS_mmm`, with atomic `_01`/`_02` collision suffixes and a timezone-aware `run_manifest.json`. Unselected pipeline and optional artifact directories are not created.
