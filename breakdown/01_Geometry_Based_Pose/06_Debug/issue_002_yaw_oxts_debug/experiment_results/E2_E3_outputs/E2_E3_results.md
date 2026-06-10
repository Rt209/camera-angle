# E2 + E3 實驗結果：yaw 錯誤來源

## 結論摘要

```yaml
global sign bug confirmed: false
local sign flip suspected: true
VP selection error confirmed: inconclusive
production_code_modified: false
```

重點：全域反號不是主因。反號後全部 frame MAE 從 `49.2858 deg` 變成 `72.9165 deg`，整體更差；但第 91-100 幀反號後 MAE 從 `113.0086 deg` 降到 `6.4455 deg`，顯示錯誤集中在局部 frame，較像第 91-100 幀發生 local sign / VP side / cluster 問題。

## E2 結果：sign variant

| 範圍 | frame count | original MAE | inverted MAE | 反號改善幀數 | 判讀 |
|---|---:|---:|---:|---:|---|
| 全部 frame | 154 | 49.2858 | 72.9165 | 60 | 反號後整體變差，不支持全域 sign bug。 |
| 第 91-100 幀 | 10 | 113.0086 | 6.4455 | 10 | 反號後大幅改善，支持局部 sign/VP side flip。 |
| 第 91-100 幀以外 | 144 | 44.8606 | 77.5326 | 50 | 反號後明顯變差，不支持全域 sign bug。 |
| top 10 yaw error frames | 10 | 113.0086 | 6.4455 | 10 | top 10 全在第 91-100 幀，反號後大幅改善。 |

Top 10 yaw error frames：`[91, 92, 93, 94, 95, 96, 97, 98, 99, 100]`。

E2 結論：

- `e2_global_sign_bug_confirmed = false`
- `e2_local_sign_flip_suspected = true`

原因：如果是全域 sign bug，`-pred_yaw` 應該改善全體 frame；但實際上只大幅改善第 91-100 幀，且傷害第 91-100 幀以外的大多數 frame。

## E3 結果：VP failure review

E3 鎖定 frame 88-103。資料層觀察到：

- 第 91-100 幀的 `pred_yaw` 全部為正，但 `oxts_yaw` 仍為負。
- 第 91-100 幀全部 `inversion_improves_error=true`。
- 第 91-100 幀的 selected VP x 多落在 image center 右側，與正 yaw 一致。
- frame 88-103 這段整體都呈現反號後改善，表示異常可能從 88 附近已開始，91-100 是 top error 最集中的區段。

但是：

- `outputs/video_pose/debug_frames` 不存在。
- `14_perspective_lines.png`、`15_vanishing_point_candidates.png`、`16_selected_vanishing_point.png`、`17_yaw_overlay.png` 無法視覺檢查。
- 因此無法嚴格確認 VP 是否「視覺上選錯 cluster」。

E3 結論：

```yaml
e3_vp_selection_error_confirmed: null
reason: 缺少 per-frame PNG debug artifacts，視覺層 VP selection error 無法確認；但資料層支持第 91-100 幀有局部 VP side/sign flip suspicion。
```

詳細 review 見 `vp_failure_frame_review.md`。

## 是否支持「局部 VP / 正負號 / 群集失敗」

支持，但強度分兩層：

| 命題 | 判斷 | 理由 |
|---|---|---|
| 全域 sign bug | 不支持 | 反號後 all frame MAE 變差。 |
| 局部 sign flip | 支持 | 第 91-100 幀反號後 MAE 從 113.0086 降到 6.4455。 |
| VP side / cluster failure | 資料層支持、視覺層未確認 | selected VP 使第 91-100 幀 yaw 轉正，但缺少 debug PNG，不能正式判定 wrong cluster。 |
| 兩者同時發生 | 可疑 | E2 的局部反號改善與 E3 的 VP side flip 疑點一致。 |

## 小階段驗證

| Scope | 檢查 | 狀態 | 說明 |
|---|---|---|---|
| E2 | S1 | pass | `pose_vs_oxts.csv` rows=154 |
| E2 | S2 | pass | 必要欄位存在：`frame_index`, `pred_yaw`, `oxts_yaw`, `abs_yaw_error` |
| E2 | S3 | pass | all frame MAE 已計算，original=49.2858 |
| E2 | S4 | pass | 第 91-100 幀共 10 筆，MAE 已計算 |
| E2 | S5 | pass | 反號後 MAE 已計算 |
| E2 | S6 | pass | 全域判斷同時使用 all frame 與 outside 91-100，不只看局部 frame |
| E3 | S1 | pass | frame 88-103 共 16 筆 |
| E3 | S2 | pass | 第 91-100 幀都被納入 |
| E3 | S3 | pass | 每個 frame 都有 selected VP x/y |
| E3 | S4 | pass | 每個 frame 都有 perspective line count 與 VP candidate count |
| E3 | S5 | pass | 每個 frame 都有 `correct`, `suspicious`, `wrong`, `missing` 之一的狀態 |
| E3 | S6 | pass | E3 結論已連回 E2 sign variant 結果 |

## 最終結論

E2 + E3 的結果顯示：目前 yaw 大錯誤不是全域 sign bug。錯誤高度集中在第 91-100 幀，且這段 frame 反號後誤差大幅下降，表示更像局部 sign / VP side flip。

E3 因為缺少 per-frame debug PNG，不能正式確認 selected VP 是否選到錯誤視覺群集；但從 `selected_vanishing_point_x/y`、`pred_yaw`、`oxts_yaw` 與反號改善結果來看，第 91-100 幀確實有局部 VP / sign / cluster failure 的強烈嫌疑。

建議下一步重新產生 frame 88-103 的 debug artifacts，保留 `debug_frames`，再用 `16_selected_vanishing_point.png` 與 `15_vanishing_point_candidates.png` 做視覺確認。
