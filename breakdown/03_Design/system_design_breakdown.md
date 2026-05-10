graph TD
    %% 核心技術層級
    subgraph Technology_Stack [技術實現層]
        T1[Click / Argparse] ---|指令解析| T2[Pillow-heif]
        T2 ---|解碼串流| T3[ExifRead Library]
        T3 ---|符合 JEIDA 標準| T4[Metadata Mapping Engine]
    end

    %% JEIDA 標準標籤處理邏輯
    subgraph JEIDA_Standard [JEIDA 標準標籤處理]
        T4 --> Tag_A[光學參數標籤]
        T4 --> Tag_B[曝光控制標籤]
        T4 --> Tag_C[影像環境標籤]

        Tag_A -->|0x920a| A1(焦距 Focal Length)
        Tag_A -->|0x829d| A2(光圈 F-Number)
        
        Tag_B -->|0x829a| B1(曝光時間 Exposure Time)
        Tag_B -->|0x8827| B2(ISO 設置)
        
        Tag_C -->|0x011a| C1(解析度/單位)
        Tag_C -->|0x0110| C2(設備型號: 如 iPhone 14)
    end

    %% 數據轉換與計算模塊
    subgraph Processing_Logic [數據轉譯邏輯]
        A1 --> Calc1[幾何視角換算: FOV]
        B1 --> Calc2[分數轉小數處理: 1/120s]
        C2 --> Calc3[設備校準參數匹配]
    end

    %% 終端機呈現
    subgraph CLI_Output [Terminal 輸出實現]
        Calc1 & Calc2 & Calc3 --> UI[Rich Library Render]
        UI --> Out1[結構化彩色表格]
        UI --> Out2[JSON 數據封裝]
    end1j

    %% 樣式美化
    style Technology_Stack fill:#f5f5f5,stroke:#333,stroke-width:2px
    style JEIDA_Standard fill:#e1f5fe,stroke:#01579b
    style Processing_Logic fill:#fff3e0,stroke:#ff6f00
