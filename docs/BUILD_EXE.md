# Windows 綠色免安裝 .exe 打包教學

## 前置需求

- Windows 10/11
- Python 3.10 或以上
- 已可正常執行本專案（`py -m pytest tests/ -v` 通過）

## 方式 A：原始碼開發模式（start.bat）

1. 雙擊專案根目錄的 **`start.bat`**
2. 瀏覽器開啟 `http://localhost:8501`
3. 輸入示範閘道密碼（預設見 `.env.example`，或環境變數 `QR_ACCESS_PASSWORD`）

## 方式 B：打包成單一 .exe

### 步驟 1：安裝打包依賴

```bat
cd c:\Users\0073\Documents\trainning\2QRcode
py -m pip install -r requirements-build.txt
```

### 步驟 2：執行自動打包腳本

```bat
py build_exe.py
```

除錯時建議保留主控台視窗（預設）：

```bat
py build_exe.py
```

正式交付、不想看到黑底主控台時：

```bat
py build_exe.py --windowed
```

### 步驟 3：取得成品

打包完成後檔案位於：

```
release/
├── DualLayerQR_FusionEngine.exe   ← 雙擊執行
├── output/                        ← 生成結果寫入此處
└── 使用說明.txt
```

將整個 `release` 資料夾複製到任意路徑即可「綠色免安裝」使用。

### 步驟 4：執行 .exe

1. 雙擊 `DualLayerQR_FusionEngine.exe`
2. 約 2–5 秒後瀏覽器自動開啟
3. 輸入密碼（預設 `Dual-Layer Smart QR`，可用 `QR_ACCESS_PASSWORD` 覆寫）→ 點擊「驗證解鎖」
4. 生成的 QR 與報告輸出至 `release/output/`

> 首次啟動若防毒軟體詢問，請允許本機執行（PyInstaller 單檔 exe 常見現象）。

## 手動 PyInstaller 指令（進階）

若不想用 `build_exe.py`，可在專案根目錄執行：

```bat
py -m PyInstaller launcher.py ^
  --name DualLayerQR_FusionEngine ^
  --onefile ^
  --console ^
  --collect-all streamlit ^
  --collect-all altair ^
  --collect-all cv2 ^
  --collect-all PIL ^
  --collect-all qrcode ^
  --add-data "app_ui.py;." ^
  --add-data "run_poc.py;." ^
  --add-data "src;src" ^
  --add-data "docs;docs" ^
  --add-data "output;output" ^
  --hidden-import streamlit.web.cli
```

產出：`dist\DualLayerQR_FusionEngine.exe`

## 常見問題

| 問題 | 處理方式 |
|------|----------|
| 雙擊 exe 沒反應 | 用 `--console` 重新打包，查看錯誤訊息 |
| 瀏覽器沒自動開啟 | 手動開啟 http://localhost:8501 |
| 8501 埠被占用 | 關閉其他 Streamlit 實例，或設定環境變數 `STREAMLIT_SERVER_PORT=8502` |
| 打包體積很大（>200MB） | 正常現象（含 Streamlit + OpenCV 執行環境） |
| output 沒有檔案 | 確認 exe 同目錄下有 `output` 資料夾且可寫入 |

## 示範閘道密碼

封裝版預設登入密碼：`Dual-Layer Smart QR`（PoC 閘道，非資安機制；可用環境變數 `QR_ACCESS_PASSWORD` 覆寫）。

修改位置：`app_ui.py` 中的 `ACCESS_PASSWORD` 常數。
