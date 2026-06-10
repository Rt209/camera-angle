# E4 實驗結果：confidence 可靠度

## 結論摘要

```yaml
yaw confidence failure confirmed: true
failure concentrated in frames 91-100: false
severe top10 failures all in frames 91-100: true
confidence reliable for yaw failure: false
production_code_modified: false
```

E4 結論：`yaw_confidence` 不可靠。當 yaw error 很大時，系統仍大量給出高 yaw confidence。

## 主要結果

| 指標 | 數值 | 判讀 |
|---|---:|---|
| 全部 frame | 154 | evaluation 總筆數。 |
| `yaw_confidence >= 0.85` | 154 | 每一幀 yaw confidence 都很高。 |
| `abs_yaw_error >= 30` | 101 | 多數 frame 的 yaw error 已達 high error。 |
| `yaw_confidence_failure` | 101 | 高 yaw confidence 且 high yaw error，大量存在，failure 成立。 |
| `overall_confidence_failure` | 91 | overall confidence 也常在 yaw 大錯時維持高分。 |
| 第 91-100 幀 failure | 10 / 10 | 該區間全部是 yaw confidence failure。 |
| 第 91-100 幀以外 failure | 91 | failure 不只發生在 91-100。 |
| top 10 最嚴重 yaw error | 全部 frame 91-100 | 最嚴重錯誤集中在 91-100，而且全部高 confidence。 |

## E4 判定

| 問題 | 結果 |
|---|---|
| yaw confidence failure 是否成立？ | 成立。101 個 frame 同時滿足 `yaw_confidence >= 0.85` 與 `abs_yaw_error >= 30`。 |
| failure 是否集中在第 91-100 幀？ | 依數量看不是，因為 91-100 以外還有 91 個 failure；但最嚴重 top 10 yaw error 全部集中在 91-100。 |
| confidence 是否能反映 yaw failure？ | 不能。第 91-100 幀 yaw error 約 111-115 度，但 yaw confidence 仍為 0.98-1.00。 |

## 第 91-100 幀重點

| frame | abs_yaw_error | yaw_confidence | confidence | perspective_line_count | VP candidate count |
|---:|---:|---:|---:|---:|---:|
| 91 | 112.32 | 0.99 | 0.87 | 48 | 763 |
| 92 | 111.03 | 0.98 | 0.86 | 48 | 812 |
| 93 | 111.52 | 0.98 | 0.89 | 40 | 612 |
| 94 | 113.31 | 0.99 | 0.86 | 34 | 398 |
| 95 | 113.01 | 0.99 | 0.88 | 42 | 582 |
| 96 | 115.09 | 0.99 | 0.89 | 38 | 441 |
| 97 | 114.64 | 0.99 | 0.87 | 34 | 398 |
| 98 | 111.93 | 0.99 | 0.88 | 22 | 153 |
| 99 | 113.41 | 0.99 | 0.89 | 20 | 119 |
| 100 | 113.84 | 1.00 | 0.91 | 18 | 110 |

判讀：第 91-100 幀的 yaw 明顯錯誤，但 yaw confidence 幾乎滿分，表示現有 yaw confidence 沒有捕捉到 E2/E3 指出的局部 sign / VP side / cluster failure。

## 為什麼錯了還很高

程式追蹤顯示：

```text
selected_vanishing_point.confidence
-> YawEstimate.confidence
-> angle_confidence["yaw"]
-> pose_timeline.csv yaw_confidence
```

`selected_vanishing_point.confidence` 的計算主要依賴：

- support count
- perspective line count
- candidate spread

但它沒有檢查：

- selected VP 是否在語意上正確方向。
- 是否有多個 VP cluster 且選到錯誤 cluster。
- selected VP 是否發生 temporal jump。
- selected VP 是否在相鄰 frame 中突然跳邊。
- yaw sign / side 是否和時序趨勢一致。

因此只要候選點支撐看起來足夠集中，confidence 就可能很高，即使它代表的是錯誤方向或錯誤群集。

## support / candidate 數量分析

| 分析 | 結果 | 判讀 |
|---|---|---|
| VP candidate count 第 75 百分位 | 912.5 | candidate 很多通常代表交點很多，但不等於方向正確。 |
| 高 VP candidate frame 數 | 39 | 其中 7 個仍是 high yaw error。 |
| 高 VP candidate 的 mean abs yaw error | 13.34 deg | 候選數高時平均較好，但仍不能保證沒有高 error。 |
| perspective line count 第 75 百分位 | 57.75 | line 多通常有幫助，但不是正確性證明。 |
| 高 perspective line frame 數 | 39 | 其中 6 個仍是 high yaw error。 |
| 高 perspective line 的 mean abs yaw error | 11.27 deg | 支撐線多時平均較好，但仍可能選錯方向。 |

關鍵：第 91-100 幀不一定是 candidate count 最高的 frame，但 yaw confidence 仍接近 1.0。這表示 confidence 不只是「候選數多」的問題，而是缺少判斷 VP 是否正確、穩定、無歧義的特徵。

## 小階段驗證

| 檢查 | 狀態 | 說明 |
|---|---|---|
| S1 | pass | `pose_vs_oxts.csv` rows=154。 |
| S2 | pass | 必要欄位存在。 |
| S3 | pass | `high_yaw_confidence`, `high_yaw_error`, `yaw_confidence_failure` 已產生。 |
| S4 | pass | 全域 confidence failure 統計已輸出，yaw failure count=101。 |
| S5 | pass | 第 91-100 幀 failure 統計已輸出，10/10 都是 failure。 |
| S6 | pass | 已分析 `perspective_line_count` 與 `vanishing_point_candidate_count`。 |
| S7 | pass | 結論說明 confidence 不可靠，以及缺少 VP stability / ambiguity / temporal jump 指標。 |

## 最終結論

E4 成立：目前 yaw confidence failure 明確存在。

現有 yaw confidence 可以反映「VP 候選點是否看起來有支撐」，但不能反映「VP 是否選對方向」。這和 E2/E3 的結果一致：第 91-100 幀疑似局部 VP side / sign / cluster failure，但 yaw confidence 仍維持 0.98-1.00。

## 後續建議

1. 新增 `vp_temporal_jump`：檢查 selected VP 與前後 frame 的位移是否突然跳變。
2. 新增 `vp_side_flip`：檢查 VP 在 image center 左右側是否突然翻轉。
3. 新增 `vp_cluster_ambiguity`：比較最佳 cluster 與第二 cluster 的分數差距。
4. 新增 `vp_spread` 與 `cluster_spread` 分層指標：不要只看整體 candidate spread。
5. 新增 `line_support_consistency`：確認支撐 selected VP 的線是否來自主道路/主要透視方向，而不是非道路或次要結構。
