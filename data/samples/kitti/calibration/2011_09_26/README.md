# KITTI 2011-09-26 calibration

Source archive: `2011_09_26_calib.zip` from the KITTI Raw Data calibration link for `2011_09_26_drive_0005_sync`.

The repository sample `images/0000000000.png` is byte-identical to `image_03/data/0000000000.png` in the synced drive archive (SHA-256 `57EDD55D7D4D91277E4CAD42EC47258BB799FEFBF643B7E1D16B6EC09A2B7E9B`). Therefore this project uses the rectified right color camera profile `P_rect_03` / `S_rect_03`.

The MP4 encoder represents the original `1242x375` frames as `1242x374` by dropping the final row. The principal point and focal length are not rescaled for this one-row codec crop.
