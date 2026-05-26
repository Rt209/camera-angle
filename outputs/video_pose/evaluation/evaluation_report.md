# 影片姿態偵測 vs KITTI OXTS 評估報告

日期：2026-05-26

## 報告目的

這份報告整理 `outputs/video_pose/evaluation` 中的評估輸出，說明每個 CSV / JSON / PNG 檔案的意義，以及目前從圖表和統計數字看到的初步結果。

本次評估比較的是：

- 幾何姿態偵測輸出：`outputs/video_pose/pose_timeline.csv`
- KITTI 官方 OXTS 姿態資料：`tools/input/oxts`

注意：OXTS yaw / pitch / roll 是車輛姿態資料；目前 geometry pipeline 的 yaw / pitch / roll 是從影像線條、地平線、消失點估出的 visual pose。兩者可以對照，但不一定是完全相同的物理量。

## 評估輸入

```text
pose_timeline.csv rows: 154
OXTS pose records: 對應 frame 0 到 frame 153
```

本次使用逐幀結果，也就是影片每一幀都處理一次。

## 評估輸出檔案

### `pose_vs_oxts.csv`

逐幀對照表。

每一列代表一個 frame，包含：

- predicted yaw / pitch / roll
- OXTS yaw / pitch / roll
- error = predicted - OXTS
- abs_error = abs(error)
- confidence
- line / horizon / vanishing point feature counts
- status

用途：

- 找出每一幀和 OXTS 的差異。
- 分析誤差是否和 confidence 或 feature count 有關。
- 作為後續挑選 debug frame 的主要資料來源。

### `pose_vs_oxts_summary.json`

整體統計摘要。

包含：

- total rows
- yaw / pitch / roll valid count
- mean absolute error
- median absolute error
- max absolute error
- RMSE
- yaw / pitch / roll worst frames top 10

用途：

- 快速判斷哪個角度最不穩。
- 找出最需要檢查的 frame index。
- 比較未來不同版本演算法或不同影片的結果。

### `worst_frames.csv`

誤差最大的 frame 清單。

它分別列出：

- yaw error 最大的 frame
- pitch error 最大的 frame
- roll error 最大的 frame

用途：

- 後續若要開啟 debug artifacts，優先看這些 frame。
- 不需要人工掃完整支影片。

## 圖片說明

### 1. `yaw_pred_vs_oxts.png`

![Yaw predicted vs OXTS](yaw_pred_vs_oxts.png)

意義：

- x 軸是 `frame_index`
- y 軸是 yaw degree
- 一條線是 geometry pipeline 預測的 yaw
- 一條線是 KITTI OXTS yaw

目前觀察：

- 前段 predicted yaw 與 OXTS yaw 有部分趨勢接近。
- 中後段 predicted yaw 轉為正值，但 OXTS yaw 仍為負值。
- yaw 差異最大集中在 frame 91 到 frame 100 附近。
- 這支持目前的判斷：geometry yaw 受到 vanishing point / 影像結構影響，不能直接等同 OXTS global heading。

### 2. `pitch_pred_vs_oxts.png`

![Pitch predicted vs OXTS](pitch_pred_vs_oxts.png)

意義：

- x 軸是 `frame_index`
- y 軸是 pitch degree
- 比較 geometry pitch 與 OXTS pitch

目前觀察：

- pitch 整體誤差比 yaw 小很多。
- mean absolute pitch error 約為 `1.3891` 度。
- 最大 pitch error 約為 `5.2549` 度。
- pitch 在部分 frame 有偏移，但整體仍比 yaw 穩定。

### 3. `roll_pred_vs_oxts.png`

![Roll predicted vs OXTS](roll_pred_vs_oxts.png)

意義：

- x 軸是 `frame_index`
- y 軸是 roll degree
- 比較 geometry roll 與 OXTS roll

目前觀察：

- roll 整體誤差也比 yaw 小。
- mean absolute roll error 約為 `1.5228` 度。
- 最大 roll error 約為 `5.2153` 度。
- roll 仍有少數局部 frame 誤差較大，但沒有 yaw 那種大幅正負方向分歧。

### 4. `abs_error_by_frame.png`

![Absolute error by frame](abs_error_by_frame.png)

意義：

- x 軸是 `frame_index`
- y 軸是 absolute error degree
- 同時畫出 yaw / pitch / roll 的絕對誤差

目前觀察：

- yaw absolute error 明顯高於 pitch / roll。
- pitch / roll 多數 frame 都維持在較小誤差範圍。
- yaw 在 frame 91 到 frame 100 附近出現最高誤差區段。

用途：

- 這張圖最適合用來快速找出「哪一段影片最需要 debug」。

### 5. `confidence_vs_abs_error.png`

![Confidence vs absolute error](confidence_vs_abs_error.png)

意義：

- x 軸是 pipeline output 的 overall confidence
- y 軸是 absolute error degree
- yaw / pitch / roll 分別以 scatter 呈現

目前觀察：

- pitch / roll 即使 confidence 高，誤差通常仍相對小。
- yaw 有些 frame confidence 很高，但 OXTS error 也很高。
- 這表示目前 confidence 比較像「單幀影像幾何特徵內部一致性」，不一定代表「和 OXTS global pose 的一致性」。

重要解讀：

- 這不是單純 confidence 寫錯。
- 比較合理的理解是：geometry estimate 和 OXTS pose 的定義不同，所以 confidence 高只代表 geometry pipeline 對自己的 vanishing point / horizon selection 有信心。

## 主要統計結果

```text
total_rows: 154
valid_yaw_count: 154
valid_pitch_count: 154
valid_roll_count: 154
```

```text
mean_abs_yaw_error: 49.2858
median_abs_yaw_error: 52.0403
max_abs_yaw_error: 115.0878
rmse_yaw_error: 61.5331
```

```text
mean_abs_pitch_error: 1.3891
median_abs_pitch_error: 1.0531
max_abs_pitch_error: 5.2549
rmse_pitch_error: 1.8433
```

```text
mean_abs_roll_error: 1.5228
median_abs_roll_error: 1.1684
max_abs_roll_error: 5.2153
rmse_roll_error: 1.9023
```

## Worst Yaw Frames

目前 yaw error 最大的 frame：

```text
rank 1: frame 96, pred_yaw 57.64, oxts_yaw -57.4478, abs_error 115.0878, confidence 0.89
rank 2: frame 97, pred_yaw 55.78, oxts_yaw -58.8603, abs_error 114.6403, confidence 0.87
rank 3: frame 100, pred_yaw 50.52, oxts_yaw -63.3176, abs_error 113.8376, confidence 0.91
rank 4: frame 99, pred_yaw 51.55, oxts_yaw -61.8571, abs_error 113.4071, confidence 0.89
rank 5: frame 94, pred_yaw 58.78, oxts_yaw -54.5283, abs_error 113.3083, confidence 0.86
```

初步判斷：

- yaw 大誤差集中在同一段影片，而不是隨機分散。
- 這比較像場景幾何或 yaw 定義問題，而不是單幀偶發 crash。
- 如果之後要繼續研究 geometry-only yaw，應先針對 frame 91 到 100 產生 debug artifacts。

## 結論

本次 evaluation 的主要結論是：

```text
pitch / roll 與 OXTS 的數值差異相對小。
yaw 與 OXTS 的差異很大，尤其集中在 frame 91 到 frame 100。
目前 geometry yaw 不適合直接當作 KITTI OXTS global heading。
```

因此，如果下一階段目標是提升實驗可控性，與其針對這支影片硬調 geometry 參數，更合理的方向是重新定義新的實驗條件，例如光源輔助、可控場景、或更明確的座標定義。

## 後續建議

如果繼續做 geometry-only 評估：

```text
1. 針對 frame 91 到 100 產生 debug artifacts。
2. 檢查 selected vanishing point 是否被場景線條帶偏。
3. 檢查 yaw 定義是否需要和 OXTS 做座標系對齊。
```

如果轉向光源輔助實驗：

```text
1. 先定義光源輸入形式。
2. 定義光源在畫面中的可觀測特徵。
3. 定義 ground truth 與 expected output。
4. 再設計新的 evaluation 指標。
```
