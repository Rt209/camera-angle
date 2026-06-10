# E3 VP failure frame review

範圍：frame 88-103。

注意：本次 `outputs/video_pose/debug_frames` 不存在，因此 PNG artifacts 無法視覺確認；以下 VP 狀態主要根據 selected VP 座標、yaw sign variant、line/candidate counts 做資料層判斷。

| frame | pred_yaw | oxts_yaw | abs_err | inv_abs_err | improves | VP x | VP y | side | x_delta | persp_lines | VP candidates | yaw_conf | artifacts | VP status | note |
|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---|---|---|
| 88 | 61.27 | -46.00 | 107.27 | 15.27 | true | 962.20 | 203.34 | right |  | 34 | 340 | 0.97 | missing | `suspicious` | 缺少 debug artifacts，無法視覺確認 VP 是否合理；資料層顯示反號後改善。 |
| 89 | 55.12 | -47.53 | 102.65 | 7.59 | true | 889.29 | 197.80 | right | -72.91 | 37 | 478 | 0.95 | missing | `suspicious` | 缺少 debug artifacts，無法視覺確認 VP 是否合理；資料層顯示反號後改善。 |
| 90 | 60.05 | -48.91 | 108.96 | 11.14 | true | 945.58 | 195.46 | right | 56.29 | 42 | 635 | 0.97 | missing | `suspicious` | 缺少 debug artifacts，無法視覺確認 VP 是否合理；資料層顯示反號後改善。 |
| 91 | 62.01 | -50.31 | 112.32 | 11.70 | true | 972.78 | 193.15 | right | 27.20 | 48 | 763 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 92 | 59.20 | -51.83 | 111.03 | 7.37 | true | 934.67 | 192.83 | right | -38.11 | 48 | 812 | 0.98 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 93 | 58.35 | -53.17 | 111.52 | 5.18 | true | 924.35 | 191.16 | right | -10.32 | 40 | 612 | 0.98 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 94 | 58.78 | -54.53 | 113.31 | 4.25 | true | 929.49 | 189.01 | right | 5.14 | 34 | 398 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 95 | 56.97 | -56.04 | 113.01 | 0.93 | true | 908.58 | 188.75 | right | -20.91 | 42 | 582 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 96 | 57.64 | -57.45 | 115.09 | 0.19 | true | 916.10 | 186.81 | right | 7.52 | 38 | 441 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 97 | 55.78 | -58.86 | 114.64 | 3.08 | true | 895.97 | 187.19 | right | -20.13 | 34 | 398 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 98 | 51.64 | -60.29 | 111.93 | 8.65 | true | 857.29 | 194.14 | right | -38.68 | 22 | 153 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 99 | 51.55 | -61.86 | 113.41 | 10.31 | true | 856.54 | 189.65 | right | -0.75 | 20 | 119 | 0.99 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 100 | 50.52 | -63.32 | 113.84 | 12.80 | true | 847.99 | 176.77 | right | -8.55 | 18 | 110 | 1.00 | missing | `suspicious` | 第 91-100 幀 pred_yaw 為正、OXTS yaw 為負，反號後誤差大幅降低；資料層顯示局部 side/sign flip，但缺少 PNG artifacts，無法視覺確認錯誤 cluster。 |
| 101 | 45.92 | -64.88 | 110.80 | 18.96 | true | 814.09 | 179.02 | right | -33.90 | 19 | 123 | 1.00 | missing | `suspicious` | 異常後仍有反號改善，疑似 VP/scene transition 尚未恢復；需視覺 artifacts 確認。 |
| 102 | 42.41 | -66.24 | 108.65 | 23.83 | true | 791.81 | 182.24 | right | -22.28 | 17 | 95 | 0.99 | missing | `suspicious` | 異常後仍有反號改善，疑似 VP/scene transition 尚未恢復；需視覺 artifacts 確認。 |
| 103 | 40.72 | -67.58 | 108.30 | 26.86 | true | 781.98 | 178.16 | right | -9.83 | 21 | 166 | 0.99 | missing | `suspicious` | 異常後仍有反號改善，疑似 VP/scene transition 尚未恢復；需視覺 artifacts 確認。 |
