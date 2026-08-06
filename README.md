# 雙資訊 QR Code 融合引擎

依 Zhou & Wang (*Sensors* 2024) 實作**雙資訊二維碼**：一張 QR Code，**遠距離**掃描讀網址 A，**近距離**掃描讀網址 B，可用標準手機 QR 掃描器。

> 本專案為技術 PoC；實際可讀性依裝置、列印品質與掃描距離而異。  
> 核心概念來自公開論文；本倉庫為工程實作與產品原型。

## 快速開始

```bash
py -m pip install -r requirements.txt
py -m streamlit run app_ui.py
```

瀏覽器開啟後輸入示範閘道密碼（預設：`Dual-Layer Smart QR`，可用環境變數 `QR_ACCESS_PASSWORD` 覆寫）。

Windows 也可雙擊 `start.bat`。

## 線上 Demo（免費）

原始碼：https://github.com/thielip/DualLayer-QR-Fusion-Engine

**一鍵部署到 Streamlit Community Cloud（免費，前後台合一）：**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=thielip/DualLayer-QR-Fusion-Engine&branch=main&mainModule=app_ui.py)

1. 用 **GitHub 帳號 `thielip`** 登入 Streamlit Cloud（與倉庫同一帳號）
2. 確認 Repository / Branch=`main` / Main file=`app_ui.py` → Deploy  
3. （可選）Secrets 加上：`QR_ACCESS_PASSWORD = "你的密碼"`

完整說明見 **[docs/MAINTENANCE.md](docs/MAINTENANCE.md)**。

## 專案結構

```
2QRcode/
├── src/                    # 核心演算法與管線
│   ├── dual_info_qr.py     # 雙態模組融合
│   ├── matrix_fusion.py    # 融合引擎
│   ├── fusion_adaptation.py
│   ├── qr_generator.py
│   ├── image_renderer.py
│   ├── simulation.py
│   └── validator.py
├── docs/
│   ├── DEVELOPMENT.md      # 從零復刻／開發文件
│   ├── MAINTENANCE.md      # 維護與免費部署
│   ├── DUAL_INFO_MANUAL.md # 操作參數手冊
│   └── BUILD_EXE.md
├── app_ui.py               # Streamlit UI
├── run_poc.py              # CLI
├── launcher.py / build_exe.py / start.bat
└── tests/
```

## 命令列

```bash
# A4 標準列印（預設）
py run_poc.py --url-a "https://example.com/a" --url-b "https://example.com/b"

# 螢幕展示（論文參數 m=11, ω=3）
py run_poc.py --output-preset screen

# 手動參數
py run_poc.py --output-preset manual --final-size 1200 --dpi 600 --module-block-size 11 --centroid-size 3
```

## 測試

```bash
py -m pytest tests/ -v
```

## 輸出預設

| 預設 | 說明 |
|------|------|
| `screen` | 螢幕展示，m=11, ω=3 |
| `a4_print` | A4 列印 4×4 cm（預設） |
| `hi_res` | 高解析列印 |
| `large` | 大尺寸 6×6 cm |
| `manual` | 手動自訂全部參數 |

## 主要輸出

- **`output/fused_qr.png`** — 唯一送印定稿
- **`output/validation_report.json`** — 遠掃 A / 近掃 B 驗證結果

## 文件

| 文件 | 用途 |
|------|------|
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 技術開發與復刻 |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | 維護、除錯、免費上雲 |
| [docs/DUAL_INFO_MANUAL.md](docs/DUAL_INFO_MANUAL.md) | 參數與掃描技巧 |
| [docs/BUILD_EXE.md](docs/BUILD_EXE.md) | Windows exe 封裝 |

## 授權

MIT（見 `LICENSE`）。學術引用請標明 Zhou & Wang, Sensors 2024。
