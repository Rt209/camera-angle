# Debug Prompt: Optical-Flow Pose 參數修正

role: "你是一位資深 OpenCV 電腦視覺工程師與測試導向 coding agent"

task:
  name: "Optical-Flow Pose Parameter Debug"
  project_root: "C:\\Users\\GIGABYTE\\camera-angle"
  input_video: "C:\\Users\\GIGABYTE\\camera-angle\\tools\\output\\kitti_no_overlay.mp4"
  debug_root: "C:\\Users\\GIGABYTE\\camera-angle\\debug\\experiments\\optical_flow_pose"
  output_root: "C:\\Users\\GIGABYTE\\camera-angle\\outputs\\optical_flow_pose"

goal: >
  只針對 optical-flow pose prototype 做參數 debug。
  目標是降低 pitch / roll outlier，維持 relative yaw 穩定，
  並改善 confidence 對錯誤 frame 的辨識能力。

non_goals:
  - "不要調整 geometry-based pipeline。"
  - "不要修改 vanishing point / horizon / line detection。"
  - "不要做 camera calibration。此專案目前不等待 chessboard / Charuco calibration video。"
  - "不要把 relative pose 拿去跟 OXTS absolute yaw / pitch / roll 比。"
  - "不要宣稱 approximate K 結果是正式 calibrated pose。"

important_rules:
  - "目前仍使用 approximate K。每筆 pose result 必須保留 intrinsics_not_calibrated / approximate_K_used / pose_for_debug_only。"
  - "中間參數、圖片、暫存報告全部放到 debug/experiments/optical_flow_pose。"
  - "正式輸出放到 outputs/optical_flow_pose。"
  - "評估 optical-flow pose 時，只能比較 predicted frame-to-frame relative yaw/pitch/roll 與 OXTS frame-to-frame delta。"
  - "每次改程式後必須跑相關 pytest。"
  - "先做 outlier frame deep dive，再做參數 sweep，不要盲目調參。"

required_reading:
  - "breakdown/02_Optical_Flow_Pose/06_Debug/pose_estimation_experiment_design.md"
  - "outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/evaluation_report.md"
  - "outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/relative_pose_vs_oxts_summary.json"
  - "outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation/relative_pose_vs_oxts.csv"
  - "src/contexts/motion_analysis/services/sparse_flow_tracker.py"
  - "src/contexts/pose_estimation/services/essential_pose_estimator.py"
  - "src/app/optical_flow_pose_overlay_pipeline.py"

current_baseline:
  comparison_type: "predicted frame-to-frame relative rotation vs OXTS frame-to-frame delta"
  total_rows: 119
  mean_inlier_ratio: 0.5472
  mean_confidence: 0.1769
  mean_abs_yaw_error_deg: 0.9668
  mean_abs_pitch_error_deg: 1.6467
  mean_abs_roll_error_deg: 0.3920
  rmse_yaw_error_deg: 1.0794
  rmse_pitch_error_deg: 2.6577
  rmse_roll_error_deg: 1.5497
  max_abs_yaw_error_deg: 3.2510
  max_abs_pitch_error_deg: 8.8864
  max_abs_roll_error_deg: 15.3001

priority_outlier_frames:
  pitch:
    - 34
    - 35
    - 38
    - 73
    - 76
    - 77
    - 79
    - 80
  roll:
    - 117
    - 118
    - 119
  yaw:
    - 86
    - 97
    - 101
    - 103
    - 117

baseline_commands:
  sparse_flow: >
    python tools/analyze_optical_flow_paths.py
    --video tools/output/kitti_no_overlay.mp4
    --debug-dir outputs/optical_flow_pose/sparse_flow
    --frame-step 1
    --max-debug-frames 120
    --output-debug-every-n-frames 10

  pose_overlay: >
    python tools/write_uncalibrated_pose_overlay.py
    --video tools/output/kitti_no_overlay.mp4
    --debug-dir outputs/optical_flow_pose/pose_overlay_uncalibrated
    --max-debug-frames 120
    --output-debug-every-n-frames 10

  evaluation: >
    python tools/evaluate_uncalibrated_pose_overlay_against_oxts.py
    --pose-json outputs/optical_flow_pose/pose_overlay_uncalibrated/frame_pose_results.json
    --oxts-dir tools/input/oxts
    --output-dir outputs/optical_flow_pose/pose_overlay_uncalibrated/evaluation

debug_directory_contract:
  root: "debug/experiments/optical_flow_pose"
  each_experiment_must_save:
    - "params/config.json"
    - "metrics/relative_pose_vs_oxts_summary.json"
    - "metrics/relative_pose_vs_oxts.csv"
    - "reports/experiment_report.md"
  if_debug_images_are_generated_save:
    - "frames/frame_000079_flow_vectors.png"
    - "frames/frame_000079_inliers_outliers.png"
    - "frames/frame_000079_pose_overlay.png"
    - "frames/frame_000117_flow_vectors.png"
    - "frames/frame_000117_inliers_outliers.png"
    - "frames/frame_000117_pose_overlay.png"

experiment_order:
  - id: "001_baseline"
    goal: "保存目前 baseline metrics 與指令，不做參數修改。"
    output_dir: "debug/experiments/optical_flow_pose/001_baseline"
    required_outputs:
      - "params/config.json"
      - "metrics/relative_pose_vs_oxts_summary.json"
      - "reports/baseline_report.md"

  - id: "005_outlier_frame_deep_dive"
    goal: "先分析 pitch / roll / yaw outlier frame，判斷問題源自 tracking、RANSAC、approx K 還是 recoverPose ambiguity。"
    output_dir: "debug/experiments/optical_flow_pose/005_outlier_frame_deep_dive"
    inspect_frames:
      - 34
      - 35
      - 38
      - 73
      - 76
      - 77
      - 79
      - 80
      - 86
      - 97
      - 101
      - 103
      - 117
      - 118
      - 119
    required_per_frame_fields:
      - "tracked_point_count"
      - "valid_track_count"
      - "inlier_count"
      - "inlier_ratio"
      - "yaw_deg"
      - "pitch_deg"
      - "roll_deg"
      - "oxts_delta_yaw"
      - "oxts_delta_pitch"
      - "oxts_delta_roll"
      - "abs_yaw_error"
      - "abs_pitch_error"
      - "abs_roll_error"
      - "warnings"
    required_debug_images:
      - "input frame"
      - "flow vectors"
      - "RANSAC inliers/outliers"
      - "pose overlay"

  - id: "002_lk_feature_sweep"
    goal: "調整 Shi-Tomasi 與 LK tracking 參數，降低 pitch / roll outlier。"
    output_dir: "debug/experiments/optical_flow_pose/002_lk_feature_sweep"
    parameters:
      max_corners: [500, 1000, 1500]
      quality_level: [0.005, 0.01, 0.02]
      min_distance: [6, 8, 12]
      lk_win_size: [15, 21, 31]
      lk_max_level: [2, 3, 4]
      lk_criteria_count: [20, 30]
      lk_criteria_eps: [0.01]
    success_criteria:
      - "mean_abs_yaw_error <= baseline + 0.2 deg"
      - "mean_abs_pitch_error 改善至少 10%"
      - "max_abs_pitch_error 改善至少 20%"
      - "max_abs_roll_error 改善至少 20%"
      - "mean_inlier_ratio >= 0.5"

  - id: "003_ransac_threshold_sweep"
    goal: "調整 Essential Matrix RANSAC threshold / min_points，處理高 inlier ratio 但姿態角錯誤的 frame。"
    output_dir: "debug/experiments/optical_flow_pose/003_ransac_threshold_sweep"
    parameters:
      ransac_threshold: [0.5, 0.75, 1.0, 1.5, 2.0]
      ransac_probability: [0.999]
      min_points: [8, 20, 50]
    success_criteria:
      - "mean_abs_pitch_error 改善至少 10%"
      - "max_abs_roll_error 改善至少 20%"
      - "too_few_pose_inliers_count 不高於 baseline"

  - id: "004_approx_k_sensitivity"
    goal: "測試 approximate K 對 pitch / roll outlier 的敏感度。"
    output_dir: "debug/experiments/optical_flow_pose/004_approx_k_sensitivity"
    parameters:
      focal_scale: [0.7, 0.8, 1.0, 1.2, 1.5]
      cx_offset_ratio: [-0.02, 0.0, 0.02]
      cy_offset_ratio: [-0.02, 0.0, 0.02]
    k_formula: >
      f = max(width, height) * focal_scale;
      cx = width / 2 + width * cx_offset_ratio;
      cy = height / 2 + height * cy_offset_ratio
    success_criteria:
      - "找到一組 approximate K，使 pitch / roll outlier 明顯下降"
      - "結果仍必須標示 approximate_K_used"

  - id: "006_confidence_calibration"
    goal: "改善 confidence 對錯誤 frame 的辨識能力，加入 unreliable warnings。"
    output_dir: "debug/experiments/optical_flow_pose/006_confidence_calibration"
    candidate_factors:
      - "inlier_ratio"
      - "valid_track_count"
      - "median_flow_magnitude"
      - "angle_delta_stability"
      - "translation_direction_stability"
      - "pose_outlier_penalty"
      - "intrinsics_quality"
      - "inlier_spatial_distribution"
    definitions:
      high_confidence_high_error: "confidence >= 0.3 and max(abs_yaw_error, abs_pitch_error, abs_roll_error) >= 3 deg"
      unreliable: "max(abs_yaw_error, abs_pitch_error, abs_roll_error) >= 3 deg"
    success_criteria:
      - "high_confidence_high_error_count 降低至少 30%"
      - "unreliable_warning_recall >= 0.7"
      - "mean_confidence 不低於 baseline 太多"

evaluation_metrics:
  required:
    - "mean_abs_yaw_error"
    - "mean_abs_pitch_error"
    - "mean_abs_roll_error"
    - "rmse_yaw_error"
    - "rmse_pitch_error"
    - "rmse_roll_error"
    - "max_abs_yaw_error"
    - "max_abs_pitch_error"
    - "max_abs_roll_error"
    - "mean_inlier_ratio"
    - "mean_confidence"
    - "low_inlier_frame_count"
    - "high_confidence_high_error_count"
    - "unreliable_warning_precision"
    - "unreliable_warning_recall"

decision_rules:
  accept_new_parameters_if:
    - "relative yaw 不明顯惡化"
    - "pitch 或 roll outlier 明顯下降"
    - "mean_inlier_ratio >= 0.5"
    - "warnings 仍包含 approximate_K_used / intrinsics_not_calibrated / pose_for_debug_only"
  reject_new_parameters_if:
    - "mean_abs_yaw_error 比 baseline 增加超過 0.2 deg"
    - "mean_inlier_ratio < 0.5"
    - "pitch / roll outlier 沒有改善"
    - "任何結果被誤標示為 calibrated pose"

required_tests:
  - "pytest tests/test_sparse_flow_tracker.py"
  - "pytest tests/test_euler_angle_converter.py"
  - "pytest tests/test_essential_pose_estimator.py"
  - "pytest tests/test_uncalibrated_pose_overlay_pipeline.py"
  - "pytest tests/test_evaluate_uncalibrated_pose_overlay_against_oxts.py"

final_report_should_include:
  - "實驗 ID"
  - "實驗目的"
  - "修改的參數"
  - "baseline metrics"
  - "new metrics"
  - "改善百分比"
  - "outlier frame 分析"
  - "是否接受新參數"
  - "剩餘風險：仍是 approximate K"
  - "下一步建議"

first_action_for_agent: >
  先建立 001_baseline 與 005_outlier_frame_deep_dive。
  不要直接開始大範圍 sweep。
  儲存 outlier frame 的 flow vectors、RANSAC inliers/outliers、pose overlay、per-frame JSON，
  然後根據 deep dive 結果決定先做 LK sweep、RANSAC sweep，或 approximate K sensitivity。
