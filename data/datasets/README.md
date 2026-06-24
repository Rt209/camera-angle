# User Datasets

所有自行下載或拍攝的資料都放在此目錄。每一批資料使用一個獨立的 sequence ID，例如：

```text
data/datasets/
└── kitti/
    └── 2011_09_26_drive_0005_sync/
        ├── images/
        │   ├── 0000000000.png
        │   └── 0000000001.png
        ├── calibration/
        │   ├── calib_cam_to_cam.txt
        │   ├── calib_imu_to_velo.txt
        │   └── calib_velo_to_cam.txt
        ├── references/
        │   └── oxts/
        │       ├── 0000000000.txt
        │       └── 0000000001.txt
        └── dataset.json
```

## KITTI 原始資料對應

| 下載資料內的位置 | 放置位置 |
|---|---|
| `image_03/data/*.png` | `<sequence>/images/` |
| `oxts/data/*.txt` | `<sequence>/references/oxts/` |
| `calib_cam_to_cam.txt` | `<sequence>/calibration/` |
| `calib_imu_to_velo.txt` | `<sequence>/calibration/` |
| `calib_velo_to_cam.txt` | `<sequence>/calibration/` |

`dataset.json` 建議內容：

```json
{
  "dataset_type": "kitti_raw",
  "sequence_id": "2011_09_26_drive_0005_sync",
  "camera_index": "03",
  "fps": 10,
  "images_rectified": true
}
```

## 檢查條件

匯入後至少確認：

1. 圖片依檔名排序後是正確的時間順序。
2. 圖片與 OXTS 數量相同。
3. 每個圖片檔名都能找到同名的 OXTS，例如 `0000000000.png` 對應 `0000000000.txt`。
4. Calibration 日期、camera index 與該 sequence 相符。

## 輸出位置

請勿把合成影片或評估報告放回此目錄。所有執行結果使用：

```text
outputs/<run_id>/
```

目前 CLI 可以透過參數直接指定這些資料夾；後續可再加入 dataset importer，將複製、驗證及 `dataset.json` 建立流程自動化。

CMD 測試指令請見 [OPTICAL_EVALUATION_CMD.md](OPTICAL_EVALUATION_CMD.md)。
