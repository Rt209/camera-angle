graph TD
    %% 1. Use Case 模組
    subgraph Use_Case_Analysis [Use Case: 使用者意圖分析]
        UC1[使用者輸入指令與路徑] --> UC2[系統驗證檔案合法性]
        UC2 --> UC3[系統解析二進位標籤]
        UC3 --> UC4[終端機呈現格式化數據]
    end

    %% 2. User Workflow 模組
    subgraph Workflow [流程圖: 使用者操作流程]
        Start([開始]) --> Input[輸入: python main.py --path IMG.HEIC]
        Input --> Check{檔案格式支援?}
        Check -- No --> Error[顯示: 格式不支援或路徑錯誤]
        Check -- Yes --> Load[加載 HEIF/JPEG 標頭數據]
        Load --> Parse[依照 JEIDA 標準映射 Tag]
        Parse --> Render[終端機 Rich Table 渲染]
        Render --> End([結束])
    end

    %% 3. Data Model 模組
    subgraph Data_Structure [資料模型: EXIF 結構化分析]
        direction LR
        EXIF_File{EXIF 檔案結構}
        EXIF_File --> Header[Header: TIFF/JPEG 標識]
        EXIF_File --> IFD0[IFD0: 設備資訊 - 廠牌/型號]
        EXIF_File --> IFD_Exif[Exif SubIFD: 攝影參數]
        IFD_Exif --> Tags[Tags 數據集合]
        
        Tags --- T1(0x829a: 曝光時間)
        Tags --- T2(0x829d: 光圈值)
        Tags --- T3(0x8827: ISO 設置)
        Tags --- T4(0x920a: 焦距)
    end

    %% 4. Functional Requirements 模組
    subgraph Requirements [功能需求分析]
        R1[需求: 多格式支援] --- Tech1(技術: Pillow-heif 引擎)
        R2[需求: JEIDA 標準標籤] --- Tech2(技術: ExifRead 映射字典)
        R3[需求: 終端機互動] --- Tech3(技術: CLI 參數解析與表格渲染)
    end

    %% 關聯線
    Use_Case_Analysis ==> Workflow
    Workflow ==> Data_Structure
    Data_Structure ==> Requirements
