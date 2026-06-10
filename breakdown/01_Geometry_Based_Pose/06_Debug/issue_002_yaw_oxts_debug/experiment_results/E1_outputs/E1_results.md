# E1 實驗結果：pred_yaw 與 oxts_yaw 是否同語意

## 重點結論

```yaml
H1 confirmed: true
same_semantics: false
current comparison_type: geometry_single_frame_yaw_vs_oxts_absolute_heading
production_code_modified: false
```

白話結論：

目前 `pose_vs_oxts.csv` 的 `pred_yaw` 和 `oxts_yaw` 不是同一種 yaw。

`pred_yaw` 是從單張影像的 vanishing point 推出來的影像幾何 yaw。  
`oxts_yaw` 是 KITTI raw OXTS 記錄的車輛 absolute heading / reference pose yaw。

所以目前的 `yaw_error = pred_yaw - oxts_yaw` 只能當 debug signal，不能直接解讀為 calibrated absolute heading error。

## 結果對應證據

| 結果 | 對應證據 | 判讀 |
|---|---|---|
| `pred_yaw` 來自單張影像 vanishing point | `src/app/pipeline.py` 中 `run_stage_4_7_pose_pipeline_on_frame` 先呼叫 `detect_vanishing_point`，再呼叫 `estimate_yaw` | geometry yaw 是 image-based，不是 OXTS pose |
| `pred_yaw` 使用 VP x 偏移計算 | `src/contexts/pose_estimation/services/yaw_estimator.py` 使用 `degrees(atan((vanishing_point.x - center_x) / focal_length))` | yaw 語意是 vanishing-point-based approximation |
| `pred_yaw` 沒有用 OXTS | geometry pipeline 的輸入是 `Frame`，沒有讀取 `tools/input/oxts/*.txt` | pred_yaw 不是用 OXTS 對齊後的 yaw |
| `pred_yaw` 沒有用前後幀姿態 | `src/app/video_pipeline.py` 對每個 sampled frame 獨立呼叫 `run_stage_4_7_pose_pipeline_on_frame`；`smoothed_yaw` 寫入 `None` | pred_yaw 不是 temporal / frame-to-frame pose |
| `pose_timeline.csv` 的 `yaw` 直接變成 evaluation 的 `pred_yaw` | `VideoPoseFrameResult.to_timeline_row` 寫出 `yaw`；`tools/evaluate_video_pose_against_oxts.py` 用 `pred_yaw = row["yaw"]` | 中間沒有語意轉換 |
| `oxts_yaw` 來自 KITTI raw OXTS | `tools/kitti_pose_video.py` 的 `parse_pose_text` 使用 `values[5]` 作為 `yaw_rad` | oxts_yaw 是 OXTS record 的 yaw |
| `oxts_yaw` 有轉成 degrees | `tools/kitti_pose_video.py` 使用 `math.degrees(yaw_rad)` 產生 `PoseAngles.yaw_deg` | 單位與 pred_yaw 都是 degree，但語意不同 |
| evaluation 直接相減 | `tools/evaluate_video_pose_against_oxts.py` 中 `yaw_error = _error(row["yaw"], pose.yaw_deg)` | 目前是 direct subtraction |
| evaluation 沒有座標系對齊 | `tools/evaluate_video_pose_against_oxts.py` 沒有 camera-to-vehicle、vehicle-to-world、Euler order alignment 或 angle convention alignment | 嚴格 pose comparison 條件不足 |
| summary 沒有標記比較語意 | `outputs/video_pose/evaluation/pose_vs_oxts_summary.json` 只有 error metrics，沒有 `comparison_type` 或 `calibrated_pose=false` | 報告容易被誤讀 |

## Step 1：geometry yaw 來源

追蹤路徑：

```text
run_video_pose_pipeline
-> run_stage_4_7_pose_pipeline_on_frame
-> detect_vanishing_point
-> estimate_yaw
-> build_pose_result
-> VideoPoseFrameResult.to_timeline_row
-> pose_timeline.csv
```

確認結果：

| 問題 | 結果 |
|---|---|
| `pose_timeline.csv` 的 `yaw` 是否來自單張影像 vanishing point？ | 是 |
| 是否使用 `yaw = atan((vp_x - center_x) / focal_length_pixels)`？ | 是 |
| 是否使用 OXTS？ | 否 |
| 是否使用前後幀資訊？ | 否 |

關鍵判讀：

`pred_yaw` 是 single-frame vanishing-point-based image geometry yaw。

## Step 2：OXTS yaw 來源

追蹤路徑：

```text
tools/kitti_pose_video.py
-> parse_pose_text
-> load_poses
-> tools/evaluate_video_pose_against_oxts.py
```

確認結果：

| 問題 | 結果 |
|---|---|
| `oxts_yaw` 是否來自 KITTI raw OXTS？ | 是 |
| KITTI raw OXTS 是否使用 `values[5]` 作為 yaw radians？ | 是 |
| 是否轉成 degrees？ | 是 |
| 是否代表 reference / absolute pose，而不是 image vanishing point yaw？ | 是 |

關鍵判讀：

`oxts_yaw` 是 KITTI OXTS absolute heading / reference pose yaw。

## Step 3：evaluation 是否直接比較

evaluation 實際邏輯：

```text
pred_yaw = row["yaw"]
oxts_yaw = pose.yaw_deg
yaw_error = pred_yaw - oxts_yaw
```

確認結果：

| 問題 | 結果 |
|---|---|
| 是否直接比較 geometry yaw 與 OXTS yaw？ | 是 |
| 是否有做相機座標轉換？ | 否 |
| 是否有做 vehicle-to-camera transform？ | 否 |
| 是否有做 Euler rotation order 對齊？ | 否 |
| 是否有標記 `comparison_type`？ | 否 |

關鍵判讀：

目前 evaluation 是 direct numeric comparison，不是 calibrated pose comparison。

## 語意對照

| 欄位 | 來源 | 語意 | 姿態類型 |
|---|---|---|---|
| `pred_yaw` | `pose_timeline.csv` 的 `yaw` | 由影像線段與消失點推得的方向角 | single-frame image geometry approximation |
| `oxts_yaw` | KITTI raw OXTS `values[5]` | 車輛在 reference/world 座標中的 yaw / heading | absolute reference pose |

兩者雖然都是 degree，但不是同座標系、同語意、同姿態類型。

## E1 判定

```yaml
comparison_type:
  current: geometry_single_frame_yaw_vs_oxts_absolute_heading
  expected_if_strict: >
    需要將 pred_yaw 轉成與 OXTS yaw 相同 reference frame、相同 coordinate system、
    相同 pose type 的 heading，並明確處理 camera-to-vehicle / vehicle-to-world transform、
    Euler rotation convention、angle wrapping。

pose_semantics:
  pred_yaw: single_frame_vanishing_point_based_image_geometry_yaw
  oxts_yaw: kitti_oxts_absolute_heading_yaw

same_semantics:
  true_or_false: false
  reason: pred_yaw 是影像消失點近似角度，oxts_yaw 是 OXTS absolute heading，evaluation 沒有語意或座標轉換。

H1_confirmed:
  true_or_false: true
  evidence:
    - geometry yaw 來自 selected vanishing point。
    - OXTS yaw 來自 KITTI raw OXTS values[5]。
    - evaluation 直接做 row["yaw"] - pose.yaw_deg。
```

## 最終結論

H1 成立。

目前 yaw error 大，不能直接解釋成「geometry pose pipeline 的車輛 yaw 預測錯很多」。更精準的說法是：

```text
目前比較把 single-frame image geometry yaw
直接拿去比 KITTI OXTS absolute heading，
但兩者尚未做 pose semantics / coordinate frame 對齊。
```

因此目前 `pose_vs_oxts.csv` 的 yaw metrics 應標記為：

```yaml
comparison_type: geometry_single_frame_yaw_vs_oxts_absolute_heading
calibrated_pose: false
comparison_warning: not_same_coordinate_semantics
```

## 建議更新

| 文件 / 報告 | 建議更新 |
|---|---|
| `breakdown/01_Geometry_Based_Pose/06_Debug/issue_002_yaw_oxts_debug/README.md` | 標記目前 yaw comparison 是 debug signal，不是 calibrated heading evaluation |
| `outputs/video_pose/evaluation/pose_vs_oxts_summary.json` 或後續 summary | 加入 `comparison_type`、`calibrated_pose=false`、`comparison_warning` |
| `breakdown/01_Geometry_Based_Pose/02_Analysis/README.md` | 在 A6/A10 補充 VP yaw 與 OXTS yaw 的語意差異 |

