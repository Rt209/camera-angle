# Issue 002 實驗結果資料夾

本資料夾用來保存 `yaw_failure_verification_experiment.md` 中 E1-E4 的實驗 prompt、執行紀錄、輸出摘要與結論。

## 實驗清單

| 實驗 | 問題 | Prompt | 結果狀態 |
|---|---|---|---|
| E1 | yaw 是不是拿錯東西比 OXTS？ | `E1_comparison_semantics_prompt.md` | 待執行 |
| E2 + E3 | yaw 的正負號是不是在某些 frame 反了？vanishing point 是否選錯？ | `E2_E3_outputs/E2_E3_yaw_error_source_prompt.md` | 待執行 |
| E4 | yaw confidence 為什麼錯了還很高？ | `E4_outputs/E4_confidence_reliability_prompt.md` | 待執行 |

## 建議輸出結構

```text
experiment_results/
  E1_comparison_semantics_prompt.md
  E1_outputs/
    comparison_semantics_check.md
    comparison_semantics_check.json
  E2_E3_outputs/
    E2_E3_yaw_error_source_prompt.md
    E2_E3_experiment_design.md
    yaw_sign_variant_analysis.csv
    vp_failure_frame_review.md
    E2_E3_results.md
    E2_E3_summary.json
  E4_outputs/
    E4_confidence_reliability_prompt.md
    E4_experiment_design.md
    yaw_confidence_failure_analysis.csv
    E4_results.md
    E4_summary.json
```

每個實驗完成後，請把結論回寫到對應輸出資料夾，並在本 README 更新結果狀態。
