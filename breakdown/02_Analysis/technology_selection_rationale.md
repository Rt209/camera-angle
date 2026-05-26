# Technology Selection Rationale

## 1. 文件目的

本文件補充 `geometry_pose_analysis.md` 中較少明確說明的部分：

> 本專案為什麼在各階段選擇這些工具、演算法與近似方法？

`geometry_pose_analysis.md` 主要回答「哪些幾何特徵可以用來估計 yaw / pitch / roll」。本文件則補上技術選型理由，說明：

- 為什麼目前選用某項技術
- 為什麼暫時不選其他方案
- 該選擇的限制是什麼
- 未來什麼情況下應該替換或升級

本文件屬於 **02 Analysis** 階段，不定義程式碼結構，也不直接規定實作細節。實際模組邊界仍由 `03_Design/` 決定，實作順序仍由 `04_Implementation/` 決定。

---

## 2. 選型原則

本專案目前處於從 EXIF / metadata 工具轉向 visual pose estimation 的早期階段，因此技術選型優先考慮：

1. **可解釋性**：使用者可以從 debug images 看出系統為什麼得到某個角度。
2. **低依賴成本**：優先使用 OpenCV / NumPy 內建能力，避免一開始引入大型模型或複雜外部套件。
3. **可測試性**：演算法可以用 synthetic image 或 synthetic line segment 建立單元測試。
4. **可替換性**：先用簡單、穩定、可 debug 的方法建立 pipeline，再逐步替換成更強的方法。
5. **符合階段目標**：Stage 0-3 先完成 roll，Stage 4-7 再加入 pitch / yaw，不一次追求完整 3D 姿態。

---

## 3. 整體工具選擇

| 工具 / 方法 | 目前用途 | 選用原因 | 暫不選替代方案的原因 | 未來替換條件 |
|---|---|---|---|---|
| OpenCV | 影像讀取後處理、Canny、HoughLinesP、debug drawing | 成熟、穩定、文件多、電腦視覺基礎功能完整，適合 CLI 與 headless pipeline | 不直接使用深度學習框架，因為初期沒有訓練資料與模型管理需求 | 若後續需要深度估計、語意 horizon 或模型推論，可再評估 PyTorch / ONNX Runtime |
| NumPy | 影像陣列與幾何計算 | 與 OpenCV 原生整合，適合快速計算角度、距離、median、weighted score | 不需要額外數值框架 | 若計算量大到需要 GPU 或大型 batch，再評估其他方案 |
| Pillow / pillow-heif | 舊版 metadata / image loader 基礎 | 已存在於舊專案，可保留 JPEG / HEIC / HEIF 支援 | 不讓 Pillow 成為幾何分析核心，因為 OpenCV 更適合影像處理 | 若 OpenCV image loading 已完整覆蓋需求，可逐步縮小 Pillow 使用範圍 |
| Rich | CLI table output | 舊專案已使用，適合輸出可讀報告 | 不需要建立 GUI 或 web app | 若進入 realtime visualization，再考慮 OpenCV window、web UI 或其他 dashboard |

---

## 4. Stage 0-3 技術選型理由

Stage 0-3 的目標是建立第一個可交付能力：**從單張圖片估計 roll**。

### 4.1 Grayscale

| 項目 | 說明 |
|---|---|
| 選用 | OpenCV grayscale conversion |
| 原因 | edge detection 與 line detection 不需要完整 RGB 資訊，灰階可以降低資料量與參數複雜度 |
| 暫不選 | 直接使用彩色邊緣或色彩分割 |
| 暫不選原因 | roll 初版主要依賴結構線，不依賴顏色；彩色處理會增加不必要變因 |
| 風險 | 某些低對比圖片灰階後邊緣不明顯 |
| 未來升級 | 若低對比場景多，可加入 CLAHE 或自適應對比增強 |

### 4.2 Gaussian Blur

| 項目 | 說明 |
|---|---|
| 選用 | Gaussian Blur |
| 原因 | Canny 前常見降噪步驟，可減少小雜訊造成的短線段 |
| 暫不選 | Bilateral Filter、Median Filter |
| 暫不選原因 | Bilateral Filter 成本較高，Median Filter 較適合椒鹽雜訊；初版先用簡單穩定方案 |
| 風險 | 過度 blur 會抹掉細線 |
| 未來升級 | 若場景雜訊類型明確，可依圖片類型調整 filter |

### 4.3 Canny Edge Detection

| 項目 | 說明 |
|---|---|
| 選用 | Canny Edge Detection |
| 原因 | OpenCV 內建、成熟、輸出清楚 edge map，適合接 HoughLinesP |
| 暫不選 | Sobel、Scharr、CLAHE + Canny |
| 暫不選原因 | Sobel / Scharr 偏向梯度計算，不直接提供穩定二值 edge map；CLAHE 初版會增加參數與場景調整成本 |
| 風險 | 對光照、紋理、threshold 敏感 |
| 未來升級 | 若暗部或低對比圖片多，可加入 CLAHE + Canny；若邊緣破碎，可加入 morphology |

### 4.4 Probabilistic Hough Transform

| 項目 | 說明 |
|---|---|
| 選用 | OpenCV `HoughLinesP` |
| 原因 | 可直接輸出線段端點，方便計算角度、長度、orientation，也方便畫 debug images |
| 暫不選 | Standard Hough Transform、LSD、EDLines、RANSAC Line Fitting |
| 暫不選原因 | Standard Hough 輸出 rho/theta，還要額外轉換成線段；LSD / EDLines 雖可能更穩，但初期先避免額外複雜度；RANSAC 更適合後續 fitting，不是第一版 line detector |
| 風險 | 參數敏感，可能漏檢、誤檢或產生過多碎線 |
| 未來升級 | 若 HoughLinesP 對真實照片不穩，可評估 LSD / EDLines 或加入 line merging |

### 4.5 Orientation Classification

| 項目 | 說明 |
|---|---|
| 選用 | 依角度分類 near-horizontal / near-vertical / diagonal |
| 原因 | roll、horizon、vanishing point 需要不同方向的線段；分類後可讓各 context 使用明確特徵 |
| 暫不選 | 複雜 line clustering 或 Manhattan World fitting |
| 暫不選原因 | 初版只需要將線段分流給 roll / horizon / yaw，不需要完整場景結構理解 |
| 風險 | threshold 過寬會把 perspective lines 分錯類，過窄會漏掉可用線 |
| 未來升級 | 若場景線段混亂，可改成 orientation histogram clustering 或 adaptive threshold |

### 4.6 Weighted Median Roll Estimation

| 項目 | 說明 |
|---|---|
| 選用 | 以線段長度加權的 dominant orientation / weighted median |
| 原因 | 長線段通常代表較可靠結構；median 對少量離群線比 mean 穩定 |
| 暫不選 | RANSAC roll fitting、完整 Manhattan World |
| 暫不選原因 | roll 是第一個可交付角度，先用簡單可測、可 debug 的方法建立 baseline |
| 風險 | 場景中若有大量傾斜裝飾線，可能干擾 dominant orientation |
| 未來升級 | 若 roll 在多場景下不穩，可加入 line grouping、vertical-line prior 或 Manhattan World assumption |

---

## 5. Stage 4-7 技術選型理由

Stage 4-7 的目標是在 Stage 0-3 的基礎上加入 **pitch、yaw、PoseResult、confidence 與 debug output**。

### 5.1 Horizon Candidate Filtering

| 項目 | 說明 |
|---|---|
| 選用 | 從 near-horizontal lines 中篩選 horizon candidates |
| 原因 | 可直接沿用 Stage 0-3 的 LineSegment，不需要新增影像語意模型 |
| 暫不選 | Sky-ground segmentation、semantic horizon estimation |
| 暫不選原因 | 這些方法通常需要模型、資料集或較高推論成本，和目前幾何法優先的方向不一致 |
| 風險 | 室內、道路、牆面或桌面線可能被誤認為 horizon |
| 未來升級 | 若 horizon 誤判率高，可加入 vanishing point 約束、場景分類或 semantic segmentation |

### 5.2 Weighted / Dominant Horizon Selection

| 項目 | 說明 |
|---|---|
| 選用 | weighted median / dominant horizontal line selection |
| 原因 | 實作簡單、可解釋、可直接畫 debug 圖，也能用 synthetic lines 測試 |
| 暫不選 | 完整 RANSAC Horizon Fitting |
| 暫不選原因 | RANSAC 需要更多參數與測試資料；Stage 4-7 初版先建立可運作 baseline |
| 風險 | 多條平行結構線可能讓 horizon 偏移 |
| 未來升級 | 若場景中水平結構很多，可改成 RANSAC 或結合 vanishing point 推估 horizon |

### 5.3 Pitch Formula

| 項目 | 說明 |
|---|---|
| 選用 | `pitch = atan((center_y - horizon_y) / focal_length_pixels)` |
| 原因 | 這是直觀的 pinhole camera 近似，可用 horizon 相對影像中心的位置估 pitch |
| 暫不選 | 完整 camera calibration / IMU fusion |
| 暫不選原因 | 目前輸入只有單張圖片，沒有穩定內參或 IMU；完整校準會超出 Stage 4-7 範圍 |
| 風險 | focal length fallback 不準會直接影響 pitch 數值 |
| 未來升級 | 若可取得 EXIF focal length、sensor size 或 calibration profile，應替換 fallback |

### 5.4 Vanishing Point Pairwise Intersection

| 項目 | 說明 |
|---|---|
| 選用 | diagonal / perspective lines 的 pairwise intersection |
| 原因 | 可解釋、容易 debug，能直接產生 candidate points 給 voting / median selection |
| 暫不選 | J-Linkage、Mean Shift、multiple vanishing point detection |
| 暫不選原因 | 初版只需要 dominant vanishing point；複雜 clustering 需要更多資料與參數調整 |
| 風險 | 錯誤線段或近平行線會產生不穩定交點 |
| 未來升級 | 若 VP candidate 分散，可加入 RANSAC、angular residual 或 clustering |

### 5.5 Median / Voting Vanishing Point Selection

| 項目 | 說明 |
|---|---|
| 選用 | candidate intersections 的 median / support voting |
| 原因 | 比單一交點穩定，實作成本低，能先建立 yaw baseline |
| 暫不選 | RANSAC Vanishing Point Estimation |
| 暫不選原因 | RANSAC 需要定義 residual、inlier threshold、iteration 策略；初版先避免過度複雜 |
| 風險 | 多個 vanishing point 或候選點分布不單峰時，median 可能落在錯誤位置 |
| 未來升級 | 若道路、建築或室內場景出現多 VP，應改成 RANSAC / clustering / Manhattan World |

### 5.6 Yaw Formula

| 項目 | 說明 |
|---|---|
| 選用 | `yaw = atan((vp_x - center_x) / focal_length_pixels)` |
| 原因 | 用 vanishing point 水平偏移估相機左右朝向，是可解釋的 pinhole approximation |
| 暫不選 | 完整相機內外參求解 |
| 暫不選原因 | 單張圖片缺少足夠 3D 約束；完整 pose recovery 需要更明確的 calibration 或場景假設 |
| 風險 | focal length fallback 對 yaw 影響大；VP 若落在畫面外，數值可能不穩 |
| 未來升級 | 取得 calibration、可靠 FOV 或多 VP 後，應使用更完整的幾何模型 |

### 5.7 Confidence Scoring

| 項目 | 說明 |
|---|---|
| 選用 | per-angle confidence + overall confidence |
| 原因 | 單張影像估姿態不一定可靠，必須讓使用者知道每個角度的可信程度 |
| 暫不選 | 機率模型、calibrated uncertainty model |
| 暫不選原因 | 目前缺少大量標註資料，不適合宣稱統計校準過的 uncertainty |
| 風險 | heuristic confidence 可能和真實誤差不完全一致 |
| 未來升級 | Stage 8 validation framework 建立後，可做 confidence calibration |

### 5.8 Debug Visualization

| 項目 | 說明 |
|---|---|
| 選用 | 每個階段輸出 debug image 與 final pose overlay |
| 原因 | 幾何法最大的優勢是可解釋；debug 圖能幫助定位失敗原因 |
| 暫不選 | 只輸出 JSON 數值 |
| 暫不選原因 | 只看數值無法判斷是 edge、line、horizon、VP 還是公式造成錯誤 |
| 風險 | debug 圖會產生大量本機檔案 |
| 未來升級 | 將 debug artifacts 分成 local runs 與 selected snapshots，並在 validation report 中引用 |

---

## 6. 為什麼暫不使用 Deep Learning

本專案目前不以 deep learning 作為第一優先，原因如下：

1. **缺少訓練資料與標註資料**：yaw / pitch / roll 需要可靠 ground truth。
2. **推論成本較高**：模型推論、權重管理與環境部署會增加 CLI 複雜度。
3. **可解釋性較低**：使用者較難從模型輸出理解失敗原因。
4. **與階段目標不一致**：目前目標是建立幾何法 baseline 與 debug pipeline。
5. **維護成本較高**：模型版本、資料集授權、硬體差異都會增加維護負擔。

未來若幾何法在大量場景中失敗率過高，可以評估：

- semantic horizon detection
- monocular depth estimation
- learned vanishing point detection
- end-to-end camera pose estimation

但這些應該在 Stage 8 validation framework 建立後，再依據 metrics 決定。

---

## 7. 為什麼暫不做完整 Camera Calibration

完整 camera calibration 可以提升 yaw / pitch 的準確度，但目前暫不作為 Stage 0-7 的必要條件。

原因：

1. 本專案目前輸入是一般單張圖片，通常沒有 calibration target。
2. EXIF 不一定提供足夠 sensor size / focal length 資訊。
3. 不同相機、鏡頭、裁切、resize 都會影響內參。
4. Stage 0-7 的目標是先建立可運作 pipeline，而不是達成精密測量。

因此目前使用 focal length fallback：

```text
focal_length_pixels = image_width / 2
或依 debug 結果使用 min(width, height) / 2
```

這是一個 engineering approximation，不是嚴格相機模型。未來如果進入更準確驗證，應該加入：

- EXIF focal length parsing
- sensor size database
- camera profile
- calibrated intrinsics
- distortion correction

---

## 8. 技術選型與 Stage 對應

| Stage | 目標 | 目前選用 | 選用理由摘要 |
|---|---|---|---|
| Stage 1 | Image Input + Preprocessing | Pillow / OpenCV / grayscale / blur / Canny | 建立穩定影像輸入與 edge map |
| Stage 2 | Line Detection | HoughLinesP | 直接輸出線段端點，方便分類與 debug |
| Stage 3 | Roll Estimation | orientation classification + weighted median | 快速、可測、可解釋 |
| Stage 4 | Horizon + Pitch | horizontal candidate + weighted horizon | 沿用 LineSegment，避免語意模型 |
| Stage 5 | Vanishing Point + Yaw | pairwise intersection + median / voting | 建立可 debug 的 VP baseline |
| Stage 6 | PoseResult + Confidence | per-angle confidence | 支援 partial result，避免使用者誤信單一數值 |
| Stage 7 | Debug Output | overlay images | 讓失敗原因可追蹤 |
| Stage 8 | Validation | metrics / dataset / failure analysis | 用量化結果決定下一輪替換哪些技術 |

---

## 9. 與其他 Breakdown 文件的關係

| 文件 | 關係 |
|---|---|
| `requirements_breakdown.md` | 定義系統需要做到什麼，不負責選型理由 |
| `geometry_pose_analysis.md` | 說明幾何特徵與姿態角的關係 |
| `technology_selection_rationale.md` | 說明為什麼選這些技術與暫不選其他技術 |
| `bounded_context_map.md` | 定義技術應該放在哪個 Context |
| `system_design_breakdown.md` | 定義模組設計與資料流 |
| `stage_0_3_foundation_and_roll.md` | 定義 Stage 0-3 的實作任務 |
| `stage_4_7_pose_integration_and_debug.md` | 定義 Stage 4-7 的實作任務 |
| `verification_plan.md` | 定義如何驗證目前選型是否有效 |

---

## 10. 結論

本專案目前選擇 OpenCV / NumPy / Canny / HoughLinesP / weighted orientation / horizon candidates / vanishing point voting，不是因為它們一定是最終最佳解，而是因為它們符合目前階段最重要的目標：

```text
可執行、可解釋、可測試、可替換。
```

Stage 0-7 的重點是建立幾何式 visual pose estimation baseline。真正判斷這些技術是否足夠，應該交由 Stage 8 的 validation framework 透過 metrics、failure cases 與 confidence calibration 來決定。
