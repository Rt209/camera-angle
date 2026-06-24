# Data Directory

`data/` 是專案所有輸入資料的統一入口，但範例資料與使用者資料分開保存。

| 位置 | 用途 | 是否建議自行放資料 |
|---|---|---|
| `samples/` | 專案測試、文件與範例指令使用的固定資料 | 否 |
| `datasets/` | 使用者匯入的完整資料集或拍攝序列 | 是 |

## 放置原則

- 一次拍攝或一個 KITTI drive 建立一個獨立的 sequence 資料夾。
- 不要把不同 sequence 的照片或 OXTS 混在同一個資料夾。
- 原始輸入放在 `data/datasets/`，程式產生的影片、CSV、JSON 與報告一律放在 `outputs/`。
- `data/datasets/` 預設不加入 Git，避免意外提交大型或私人資料。

詳細結構請見 [datasets/README.md](datasets/README.md)。
