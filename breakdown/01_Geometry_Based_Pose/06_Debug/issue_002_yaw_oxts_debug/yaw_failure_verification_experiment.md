# Yaw Failure 驗證實驗設計

## 目的

本文件針對 issue #2 的四個核心問題設計驗證實驗：

1. yaw 是不是拿錯東西比 OXTS？
2. yaw 的正負號是不是在某些 frame 反了？
3. vanishing point 是否選錯？
4. yaw confidence 為什麼錯了還很高？

實驗目標不是馬上修改 production code，而是先確認錯誤來源。每個實驗都必須留下可追溯輸出，讓後續修正可以用 before / after metrics 驗證。

## 現有基準資料

目前使用下列資料作為基準：

```text
outputs/video_pose/evaluation/pose_vs_oxts.csv
outputs/video_pose/evaluation/pose_vs_oxts_summary.json
outputs/video_pose/evaluation/worst_frames.csv
```

現有 yaw 問題摘要：

| 範圍 | 指標 | 數值 |
|---|---|---:|
| 全部 frame | yaw MAE | 49.2858 deg |
| 全部 frame | yaw RMSE | 61.5331 deg |
| 第 91-100 幀 | yaw MAE | 113.0086 deg |
| 第 91-100 幀 | yaw 反號後 MAE | 6.4455 deg |
| 全部 frame | yaw 全域反號後 MAE | 72.9165 deg |

初步解讀：

- 全域反號不是正確修法，因為整體 yaw MAE 會變差。
- 第 91-100 幀反號後大幅改善，代表這段有局部正負號、消失點群集、或場景語意失效。
- pitch / roll 的平均誤差約 1-2 度，因此目前比較像 yaw 專屬失敗，不像整條流程全面失敗。

## 實驗總覽

| 實驗 | 對應問題 | 驗證重點 | 預期輸出 |
|---|---|---|---|
| E1 | yaw 是不是拿錯東西比 OXTS？ | 比較語意是否一致 | comparison_semantics_check.md |
| E2 | yaw 的正負號是不是在某些 frame 反了？ | 全域反號、局部反號、相對角度比較 | yaw_sign_variant_analysis.csv |
| E3 | vanishing point 是否選錯？ | 第 91-100 幀 selected VP 是否跳錯群集 | vp_failure_frame_review.md |
| E4 | yaw confidence 為什麼錯了還很高？ | 高信心分數但高誤差的 frame 是否集中 | yaw_confidence_failure_analysis.csv |

建議輸出目錄：

```text
outputs/video_pose/evaluation/issue_002_yaw_debug/
```

## E1：確認 yaw 是不是拿錯東西比 OXTS

### 要驗證的問題

```text
目前的 predicted yaw 與 OXTS yaw 是否代表同一種姿態角？
```

### 背景

目前 `outputs/video_pose/predicted_pose_overlay.mp4` 來自 geometry pipeline。這個 yaw 是從單張影像的 vanishing point 推估，是一個 image geometry yaw。

`tools/output/kitti_pose_overlay.mp4` 顯示的是 KITTI OXTS。OXTS yaw 是車體 / 世界座標中的 heading，屬於 reference pose。

因此目前比較方式是：

```text
geometry_single_frame_yaw
vs
oxts_absolute_heading
```

這個比較可以作為 debug signal，但不能直接宣稱是嚴格 calibrated pose evaluation。

### 實驗步驟

1. 讀取 `outputs/video_pose/evaluation/pose_vs_oxts.csv`。
2. 確認欄位來源：
   - `pred_yaw` 來自 geometry 單張影像估計。
   - `oxts_yaw` 來自 KITTI OXTS 絕對姿態。
3. 在報告中標記目前比較類型：

```text
comparison_type = geometry_single_frame_yaw_vs_oxts_absolute_heading
```

4. 額外產生 OXTS frame-to-frame delta：

```text
oxts_delta_yaw[t] = angle_delta(oxts_yaw[t], oxts_yaw[t-1])
```

5. 比較 `pred_yaw` 與 `oxts_yaw`，以及 `pred_yaw` 與 `oxts_delta_yaw` 的趨勢是否合理。

### 判定標準

| 結果 | 判定 |
|---|---|
| `pred_yaw` 被拿去當 calibrated absolute heading | 比較語意錯誤成立 |
| 文件或報告沒有標明 geometry yaw 是 approximate | 輸出語意文件不足 |
| `pred_yaw` 無法合理對應 OXTS absolute，也無法對應 OXTS delta | geometry yaw 只能作 debug signal，不能當正式 heading |

### 預期結論

若 E1 成立，修正方向不是先改 yaw 公式，而是先更新輸出語意：

```text
yaw_method = geometry_vanishing_point_approximation
pose_type = single_frame_approximate
calibrated_pose = false
comparison_warning = not_same_coordinate_semantics
```

## E2：確認 yaw 正負號是不是在某些 frame 反了

### 要驗證的問題

```text
yaw 的正負號是全域錯誤，還是只在某些 frame / 場景局部錯誤？
```

### 已知現象

目前已知：

| 範圍 | 原始 yaw MAE | yaw 反號後 MAE |
|---|---:|---:|
| 全部 frame | 49.2858 deg | 72.9165 deg |
| 第 91-100 幀 | 113.0086 deg | 6.4455 deg |

這代表：

- 不能直接全域反號。
- 第 91-100 幀很像局部反號、局部 VP 選錯，或局部場景 convention 失效。

### 實驗步驟

1. 針對每一幀產生下列 yaw variant：

```text
yaw_original = pred_yaw
yaw_inverted = -pred_yaw
yaw_abs_direction = abs(pred_yaw)
yaw_first_frame_relative = angle_delta(pred_yaw[t], pred_yaw[0])
oxts_first_frame_relative = angle_delta(oxts_yaw[t], oxts_yaw[0])
oxts_frame_delta = angle_delta(oxts_yaw[t], oxts_yaw[t-1])
```

2. 計算下列區間的 MAE：
   - 全部 frame。
   - 第 91-100 幀。
   - 第 91-100 幀以外。
   - top 10 yaw error frames。

3. 產生 `yaw_sign_variant_analysis.csv`：

```text
frame_index
pred_yaw
oxts_yaw
yaw_original_error
yaw_inverted_error
yaw_first_frame_relative
oxts_first_frame_relative
oxts_frame_delta
is_error_reduced_by_inversion
```

4. 畫出比較圖：

```text
yaw_original_vs_oxts.png
yaw_inverted_vs_oxts.png
yaw_error_original_vs_inverted.png
```

### 判定標準

| 結果 | 判定 |
|---|---|
| yaw 反號改善全部 frame | 全域 sign convention 錯誤 |
| yaw 反號只改善第 91-100 幀 | 局部 sign / VP / 場景失效 |
| yaw 反號改善 top error frames，但傷害其他 frame | 不可做全域反號，需做局部原因分析 |
| yaw first-frame-relative 比 absolute OXTS 更合理 | 目前輸出可能比較接近 relative / image-direction signal |

### 預期結論

目前資料已經偏向：

```text
不是全域 sign bug。
第 91-100 幀是局部錯誤，需要搭配 VP artifact 檢查。
```

## E3：確認 vanishing point 是否選錯

### 要驗證的問題

```text
第 91-100 幀的 selected vanishing point 是否選到錯誤方向或錯誤群集？
```

### 背景

geometry yaw 公式為：

```text
yaw = atan((vp_x - center_x) / focal_length_pixels)
```

因此 `selected_vanishing_point.x` 一旦落在錯誤方向，yaw 會直接變成錯誤角度。

### 實驗步驟

1. 針對下列 frame 產生或收集 debug artifacts：

```text
frame 88-103
```

這個範圍包含：

- 第 91-100 幀：主要異常區間。
- 第 88-90 幀：異常前對照。
- 第 101-103 幀：異常後對照。

2. 每一幀至少保存下列圖：

```text
14_perspective_lines.png
15_vanishing_point_candidates.png
16_selected_vanishing_point.png
17_yaw_overlay.png
```

3. 每一幀記錄下列數值：

```text
frame_index
pred_yaw
oxts_yaw
abs_yaw_error
yaw_confidence
selected_vanishing_point_x
selected_vanishing_point_y
image_center_x
focal_length_pixels
perspective_line_count
vanishing_point_candidate_count
```

4. 人工檢查每一幀的 selected VP：
   - 是否落在道路 / 車道線 / 建築物透視方向合理的位置。
   - 是否在第 91 幀附近突然跳到另一側。
   - 是否有多個 VP cluster，但系統選到錯的 cluster。
   - perspective lines 是否被非道路結構或雜訊主導。

5. 產生 `vp_failure_frame_review.md`，每個 frame 一列：

```text
frame_index
selected_vp_visual_check = correct / suspicious / wrong
dominant_scene_direction
vp_cluster_count_estimate
notes
```

### 判定標準

| 結果 | 判定 |
|---|---|
| 第 91-100 幀 selected VP 明顯落到錯誤方向 | VP 選擇錯誤成立 |
| 第 91-100 幀有多個 VP cluster，且 selected VP 選到非主 cluster | VP cluster selection 錯誤成立 |
| selected VP 視覺合理，但與 OXTS yaw 不一致 | 比較語意或座標系問題更可疑 |
| selected VP 在異常前後突然跳動 | 需要 temporal stability 檢查 |

### 預期結論

若 E3 成立，修正方向應是：

```text
1. 改善 VP clustering / voting。
2. 加入 temporal VP stability。
3. 當 VP 多群集或跳動過大時降低 yaw confidence。
4. 不要只靠 candidate count 給高 confidence。
```

## E4：確認 yaw confidence 為什麼錯了還很高

### 要驗證的問題

```text
為什麼 yaw 明顯錯誤，但 confidence 仍然高？
```

### 已知現象

第 91-100 幀 yaw error 約 111-115 deg，但 confidence 約 0.86-0.91。這表示目前 confidence 可能只看到了「有很多線、有很多 VP candidates」，卻沒有看出「選出的 VP 是否合理」。

### 實驗步驟

1. 從 `pose_vs_oxts.csv` 擷取下列欄位：

```text
frame_index
pred_yaw
oxts_yaw
abs_yaw_error
yaw_confidence
confidence
detected_line_count
perspective_line_count
vanishing_point_candidate_count
horizon_candidate_count
```

2. 建立高信心失敗條件：

```text
high_confidence = yaw_confidence >= 0.85
high_error = abs_yaw_error >= 30 deg
confidence_failure = high_confidence and high_error
```

3. 產生 `yaw_confidence_failure_analysis.csv`：

```text
frame_index
abs_yaw_error
yaw_confidence
confidence_failure
detected_line_count
perspective_line_count
vanishing_point_candidate_count
horizon_candidate_count
```

4. 計算：
   - confidence failure frame 數量。
   - confidence failure 是否集中在第 91-100 幀。
   - high candidate count 是否反而伴隨 high error。
   - yaw confidence 與 abs yaw error 的相關性。

5. 畫圖：

```text
yaw_confidence_vs_abs_error.png
candidate_count_vs_abs_yaw_error.png
confidence_failure_by_frame.png
```

### 判定標準

| 結果 | 判定 |
|---|---|
| 高 confidence 高 error 集中在第 91-100 幀 | yaw confidence 對局部 VP 失效不敏感 |
| VP candidate count 高但 yaw error 也高 | candidate 數量不能直接代表正確性 |
| yaw confidence 與 abs yaw error 無明顯負相關 | confidence formula 需要重設 |
| 加入 VP jump / cluster ambiguity 後能標出第 91-100 幀 | 新 confidence 特徵有效 |

### 建議新增 confidence 特徵

後續若要修正 confidence，可加入：

```text
vp_temporal_jump = distance(selected_vp[t], selected_vp[t-1])
vp_cluster_ambiguity = second_best_cluster_score / best_cluster_score
vp_spread = spread(vp_candidates)
vp_side_flip = sign(vp_x - center_x) changes unexpectedly
line_support_consistency = selected_cluster_line_support / total_perspective_lines
```

## 驗證順序

建議依照下列順序執行：

1. 先做 E1，確認目前比較是否語意一致。
2. 再做 E2，確認是不是全域正負號錯誤。
3. 接著做 E3，人工檢查第 91-100 幀的 VP artifact。
4. 最後做 E4，確認 confidence 為什麼沒有抓到錯誤。

原因：

- 如果 E1 顯示比較語意錯誤，後續 metrics 只能當 debug signal。
- 如果 E2 顯示不是全域 sign bug，就不能直接改 yaw 符號。
- 如果 E3 確認 VP 選錯，修正重點會放在 VP selection。
- 如果 E4 確認 confidence 失效，修正後必須讓錯誤 frame 的 confidence 降低。

## 最終決策矩陣

| E1 | E2 | E3 | E4 | 結論 | 修正方向 |
|---|---|---|---|---|---|
| 成立 | 不成立 | 不成立 | 成立 | 主要是比較語意與 confidence 文件問題 | 更新輸出語意與 report，不宣稱 calibrated heading |
| 不成立 | 全域成立 | 不成立 | 可能成立 | yaw sign convention 全域錯 | 修改 yaw 公式正負號，更新測試 |
| 不成立 | 局部成立 | 成立 | 成立 | 第 91-100 幀 VP 選錯，confidence 未偵測 | 改善 VP selection，加入 temporal / ambiguity confidence |
| 不成立 | 不成立 | 成立 | 成立 | VP 選錯但不是單純正負號 | 改善 VP clustering / voting |
| 不成立 | 不成立 | 不成立 | 成立 | yaw 方法本身不穩，confidence 太樂觀 | 文件化限制，將 heading 評估轉向 calibrated / relative pose |

## 完成條件

本實驗完成後，至少應產出：

```text
outputs/video_pose/evaluation/issue_002_yaw_debug/comparison_semantics_check.md
outputs/video_pose/evaluation/issue_002_yaw_debug/yaw_sign_variant_analysis.csv
outputs/video_pose/evaluation/issue_002_yaw_debug/vp_failure_frame_review.md
outputs/video_pose/evaluation/issue_002_yaw_debug/yaw_confidence_failure_analysis.csv
```

文件更新條件：

1. 將確認成立的錯誤寫回 `README.md`。
2. 將 before / after metrics 寫回 `README.md`。
3. 若修改程式，重新執行 evaluate，並確認 pitch / roll 沒有 regression。
