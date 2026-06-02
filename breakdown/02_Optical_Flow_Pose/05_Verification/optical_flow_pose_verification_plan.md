# Optical Flow Pose Verification Plan

## Verification Targets

| Area | Expected Check |
|---|---|
| Camera calibration | Calibration video 可產生 `K`、distortion coefficients、reprojection error，resize 後可同步縮放 |
| Optical flow paths | 可產生穩定 tracks、speed statistics、path overlay |
| Coordinate transform | pixel flow 可轉 normalized flow |
| Motion features | 可輸出 radial expansion / rotation flow score |

## First Tests

```text
tests/test_camera_calibrator.py
tests/test_sparse_flow_tracker.py
tests/test_coordinate_transforms.py
```
