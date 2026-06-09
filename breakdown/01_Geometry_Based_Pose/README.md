# Geometry Based Pose Breakdown

這是 geometry-based single image pose pipeline 的 breakdown。

此技術路線以單張影像中的幾何線索為核心：

- line detection
- horizon detection
- vanishing point detection
- yaw / pitch / roll integration
- confidence scoring
- debug artifacts

## 目前決策

此專案主流程固定採用 single-image geometry cues：

```text
Input Image
-> preprocessing
-> edge detection
-> line detection
-> horizon / vanishing point / vertical lines
-> yaw / pitch / roll
-> confidence
-> debug artifacts
```

第一版優先完成 roll estimation，接著再加入 pitch、yaw、confidence 與 validation。

若 yaw / pitch 使用 FOV 或 focal length fallback，結果必須標示為 approximate，不宣稱 calibrated absolute pose。

## 文件順序

```text
00_Overview/
01_Requirements/
02_Analysis/
03_Design/
04_Implementation/
05_Verification/
06_Debug/
```

建議進入點：

1. `00_Overview/README.md`
   - geometry-based pose 主題導覽。
2. `01_Requirements/README.md`
   - 輸入、輸出、功能與可靠性需求。
3. `02_Analysis/README.md`
   - A1-A10 模組分析、資料交換、技術工具與最終流程。
4. `03_Design/system_design_breakdown.md`
   - 系統設計與 bounded context。
5. `04_Implementation/stage_0_3_foundation_and_roll.md`
   - 第一輪 implementation roadmap。
