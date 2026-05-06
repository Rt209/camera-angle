graph TD
    %% =========================
    %% Requirement Layer
    %% =========================
    R[需求階段<br/>Photo Metadata Geometry Analyzer] --> R1[核心需求]
    R --> R2[輸入需求]
    R --> R3[資料解析需求]
    R --> R4[輸出需求]
    R --> R5[幾何推導需求]
    R --> R6[開發與驗證需求]

    %% =========================
    %% Core Requirement
    %% =========================
    R1 --> R1A[讀取照片 Metadata / EXIF]
    R1 --> R1B[整理攝影參數]
    R1 --> R1C[提供可讀的分析結果]
    R1 --> R1D[保留未來幾何分析擴充能力]

    %% =========================
    %% Input Requirement
    %% =========================
    R2 --> R2A[支援 CLI 指令輸入]
    R2 --> R2B[支援圖片路徑參數]
    R2 --> R2C[支援 JPEG / JPG]
    R2 --> R2D[支援 HEIC / HEIF]
    R2 --> R2E[檢查檔案是否存在與格式是否合法]

    R2A --> T1[Argparse / Click]
    R2C --> T2[Pillow]
    R2D --> T3[pillow-heif]

    %% =========================
    %% Metadata Requirement
    %% =========================
    R3 --> R3A[解析 EXIF 標籤]
    R3 --> R3B[讀取焦距 Focal Length]
    R3 --> R3C[讀取曝光時間 Exposure Time]
    R3 --> R3D[讀取光圈 F-Number]
    R3 --> R3E[讀取 ISO / 白平衡]
    R3 --> R3F[讀取設備型號 / 解析度 / 方向]
    R3 --> R3G[讀取 GPS 與拍攝方向資訊]

    R3A --> T4[ExifRead / Pillow EXIF]
    R3A --> T5[EXIF Tag Mapping]
    R3A --> T6[JEITA / CIPA EXIF Standard]

    %% =========================
    %% Output Requirement
    %% =========================
    R4 --> R4A[終端機表格輸出]
    R4 --> R4B[JSON 結構化輸出]
    R4 --> R4C[錯誤訊息與 Warning 顯示]
    R4 --> R4D[缺失欄位顯示 N/A]

    R4A --> T7[Rich Library]
    R4B --> T8[JSON Module]
    R4C --> T9[Error Handling]

    %% =========================
    %% Geometry Requirement
    %% =========================
    R5 --> R5A[由焦距與感光元件尺寸推導 FOV]
    R5 --> R5B[由 GPSImgDirection 取得拍攝方向]
    R5 --> R5C[預留仰角估算模組]
    R5 --> R5D[預留深度估算模組]
    R5 --> R5E[避免無資料支撐的幾何推論]

    R5A --> T10[Camera Calibration Profile]
    R5A --> T11[FOV Formula]
    R5C --> T12[Pose Estimation Placeholder]
    R5D --> T13[Depth Estimation Placeholder]

    %% =========================
    %% Development Requirement
    %% =========================
    R6 --> R6A[模組化專案架構]
    R6 --> R6B[單元測試]
    R6 --> R6C[README 使用說明]
    R6 --> R6D[可擴充的資料模型]
    R6 --> R6E[跨平台執行]

    R6A --> T14[Python src/ Layout]
    R6B --> T15[pytest]
    R6C --> T16[Markdown]
    R6D --> T17[dataclass / dict schema]
    R6E --> T18[Python 3.10+]

    %% =========================
    %% Style
    %% =========================
    style R fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style R1 fill:#f1f8e9,stroke:#33691e
    style R2 fill:#fff3e0,stroke:#ef6c00
    style R3 fill:#fce4ec,stroke:#ad1457
    style R4 fill:#ede7f6,stroke:#4527a0
    style R5 fill:#e0f2f1,stroke:#00695c
    style R6 fill:#f5f5f5,stroke:#424242