# 技術開發文件（從零復刻本專案）

本文件說明如何從原始碼**完整重建** Dual-Layer Smart QR Fusion Engine（雙資訊 QR 融合引擎）。

> 學術來源：Zhou & Wang, *Sensors* 2024, 24(10), 3055（雙資訊二維碼概念）。  
> 本倉庫為工程 PoC／產品原型，核心演算法實作見 `src/dual_info_qr.py`。

---

## 1. 系統是什麼

| 項目 | 說明 |
|------|------|
| 產品形態 | 單一 Streamlit 網頁應用（側欄＝控制台，主區＝預覽／驗證） |
| 核心能力 | 同一張 QR：遠距離掃到網址 A，近距離掃到網址 B |
| CLI | `run_poc.py` 可無 UI 跑完整管線 |
| 輸出 | `output/fused_qr.png`（唯一送印檔）+ `validation_report.json` |

**沒有獨立前後端服務**：Streamlit 同時提供 UI 與伺服端邏輯。雲端部署時也是「一個 App = 前後台合一」。

---

## 2. 環境需求

- Python **3.10+**（建議 3.11）
- Windows / macOS / Linux
- 本機開發可選：瀏覽器開啟 `http://localhost:8501`

```bash
# 建立虛擬環境（建議）
py -m venv .venv

# Windows
.venv\Scripts\activate

# 安裝依賴
py -m pip install -r requirements.txt
# 本機跑測試時再裝：
# py -m pip install -r requirements-dev.txt
```

雲端（Streamlit Community Cloud）使用 `opencv-python-headless`（已寫在 `requirements.txt`），無需本機 GUI／OpenGL。

---

## 3. 目錄結構（復刻時必備）

```
2QRcode/
├── app_ui.py                 # Streamlit UI（登入閘道 + 控制面板 + 結果）
├── run_poc.py                # CLI 與 run_pipeline()（UI／測試共用）
├── launcher.py               # Windows .exe 啟動器
├── build_exe.py              # PyInstaller 打包腳本
├── start.bat                 # Windows 一鍵啟動開發伺服器
├── requirements.txt          # 執行依賴
├── requirements-build.txt    # 打包額外依賴
├── packages.txt              # Streamlit Cloud 系統套件（目前可空）
├── .streamlit/config.toml    # 主題與瀏覽器設定
├── .env.example              # 密碼環境變數範例
├── src/
│   ├── config.py             # 預設、輸出預設、資料類別
│   ├── qr_generator.py       # QR-A / QR-B 矩陣產生與版本同步
│   ├── dual_info_qr.py       # ★ 雙態模組融合／遠近還原（核心）
│   ├── matrix_fusion.py      # 對齊與融合引擎
│   ├── fusion_adaptation.py  # 依網址長度／輸出尺寸自動調 m、ω
│   ├── image_renderer.py     # PNG 渲染
│   ├── simulation.py         # 遠近光學模擬
│   └── validator.py          # OpenCV 解碼驗證與報告
├── tests/                    # pytest 回歸測試
├── docs/
│   ├── DUAL_INFO_MANUAL.md   # 操作手冊（參數與掃描）
│   ├── BUILD_EXE.md          # Windows 封裝
│   ├── DEVELOPMENT.md        # 本文件
│   └── MAINTENANCE.md        # 維護與部署
└── examples/test_urls.json   # 範例網址
```

執行時會自動建立 `output/`（已 gitignore，勿提交產生檔）。

---

## 4. 資料流（管線）

```
URL-A, URL-B
    ↓ prepare_config_for_payloads()     # EC=L、同步 version、自動 m/ω
    ↓ QRLayerGenerator                  # 產生兩層 QR 矩陣
    ↓ MatrixFusionEngine.fuse()         # dual_info 模組融合
    ↓ ImageRenderEngine                 # fused_qr.png
    ↓ recover_near + simulation         # 近掃參考圖、遠近模擬圖
    ↓ FusionValidator                   # validation_report.json
```

關鍵參數：

| 符號 | 意義 |
|------|------|
| `m` | 每個 QR 模組放大後的像素邊長 |
| `ω` | 模組中心承載「近掃 B」的質心邊長（建議 ≈ m/3） |
| `final_size` | 輸出圖邊長（px） |
| `dpi` | PNG 中繼資料 DPI（列印用） |

詳見 `docs/DUAL_INFO_MANUAL.md`。

---

## 5. 本機執行

### 5.1 網頁 UI

```bash
py -m streamlit run app_ui.py
```

或 Windows：`start.bat`

預設示範閘道密碼：`Dual-Layer Smart QR`  
（可用環境變數 `QR_ACCESS_PASSWORD` 或 Streamlit secrets 覆寫。此閘道**不是**資安防護，僅 PoC 阻擋誤操作。）

### 5.2 CLI

```bash
py run_poc.py --url-a "https://example.com/a" --url-b "https://example.com/b" --output-preset a4_print
```

### 5.3 測試

```bash
py -m pytest tests/ -v
```

整合測試會寫入 `output/test_*`；日常開發請勿把 `output/` 提交進 Git。

---

## 6. 如何「再寫一次」同等系統

若要在另一台機器或另一語言重寫，依序實作：

1. **QR 產生**：對 URL-A／URL-B 產生相同 version、相同尺寸的二值矩陣（見 `qr_generator.py`）。
2. **雙態模組**：對每個模組，依遠／近位元組合塗黑外圈與中心 ω×ω（見 `dual_info_qr.build_dual_state_module`）。
3. **還原**：遠層用外圈多數決／規則還原；近層取中心（見 `recover_*_matrix_from_dual`）。
4. **渲染**：m 倍放大 + quiet zone + 縮放至 `final_size`。
5. **驗證**：用標準 QR 解碼器對模擬遠圖與近參考圖解碼。
6. **UI（可選）**：參數表單 → 呼叫同一 `run_pipeline`。

對照論文時，請同時閱讀 `src/dual_info_qr.py` 註解與 `docs/DUAL_INFO_MANUAL.md` §1。

---

## 7. Windows .exe（可選）

見 `docs/BUILD_EXE.md`：

```bash
py -m pip install -r requirements-build.txt
py build_exe.py
```

產物在 `release/`（gitignore）。執行檔啟動後會開本機 Streamlit。

---

## 8. 版本與授權

- 套件版本：`src/__init__.py` → `__version__`
- 授權：`LICENSE`（MIT）
- 學術引用請標明 Zhou & Wang (Sensors 2024)；本倉庫為工程實作，不代表論文作者背書。
