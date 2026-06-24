# Tests 使用指南

`tests` 依測試責任分成單元測試、整合測試與工具腳本測試。Pytest 會遞迴搜尋所有 `test_*.py`，因此可以從 repository 根目錄一次執行全部測試。

## 資料夾結構

```text
tests/
├── unit/         # 單一 service、converter、adapter 或 domain 行為
├── integration/  # 多個模組串接後的 pipeline 與影片輸出
├── tooling/      # tools 下命令列腳本的資料處理邏輯
└── README.md
```

## 分類原則

| 分類 | 測試範圍 | 特性 |
|---|---|---|
| `unit` | 單一類別、函式或小型服務 | 執行快、輸入小、失敗位置明確 |
| `integration` | Pipeline、影片讀寫、跨模組合作 | 會同時驗證多個元件的資料交換 |
| `tooling` | Dataset、Evaluation、Debug scripts | 驗證工具函式、報告欄位與統計結果 |

## 執行方式

```powershell
# 全部測試
pytest

# 只跑單元測試
pytest tests/unit

# 只跑整合測試
pytest tests/integration

# 只跑工具測試
pytest tests/tooling

# 執行單一檔案
pytest tests/unit/test_sparse_flow_tracker.py -v
```

## 新增測試

1. 依測試責任選擇 `unit`、`integration` 或 `tooling`。
2. 檔名使用 `test_<被測目標>.py`。
3. 測試函式使用 `test_<預期行為>`，讓失敗訊息能直接說明情境。
4. 暫存輸出使用 Pytest 的 `tmp_path`，不要寫進 repository 的 `outputs/`。
5. 只有需要完整 pipeline 或真實範例影片時，才放進 `integration`。
# Evaluation test architecture

Evaluation coverage includes OXTS parsing, prediction readers, source-frame alignment, rotation metrics, artifact contracts, application integration, CLI wrappers, and dependency-direction checks. Geometry keeps its 3-degree threshold and Optical keeps 1 degree, preserving pre-migration behavior.
