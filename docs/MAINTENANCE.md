# 系統維護與部署文件

給維運／未來自己的檢查清單：如何維護、除錯、免費上線。

---

## 1. 日常維護

| 頻率 | 動作 |
|------|------|
| 每次改核心演算法 | `py -m pytest tests/ -v` |
| 每次改 UI | 本機 `streamlit run app_ui.py` 走一遍：登入 → 生成 → 三個分頁 |
| 依賴升級 | 先在虛擬環境升級，跑測試後再改 `requirements.txt` |
| 清垃圾 | 可刪 `output/`、`.pytest_cache/`、`build/`、`dist/`、`release/`（皆可重建） |

### 常見問題

| 現象 | 可能原因 | 處理 |
|------|----------|------|
| 近掃 B 失敗 | m／ω 不合、列印模糊、距離不對 | 換 `a4_print`／手動調小 ω；見操作手冊 |
| Cloud 部署失敗（cv2／requirements） | 依賴或 `packages.txt` 不相容 | 確認根目錄 `requirements.txt` 使用 `opencv-python-headless`；`packages.txt` 僅含 `libgl1`（勿寫註解）；App 設定選 Python **3.11** 後 Reboot |
| OpenCV 解碼空結果 | 圖太小或對比不足 | 提高 `final_size`／DPI 預設 |

### 示範密碼政策

- 預設字串僅為 **PoC 閘道**，原始碼公開後任何人都能看到／繞過。
- 正式對外若仍要閘道：在 Streamlit Cloud → **Settings → Secrets** 設定：

```toml
QR_ACCESS_PASSWORD = "你的自訂密碼"
```

---

## 2. 本專案的「前後台」說明

本系統是 **Streamlit 單體應用**：

- 「前台」＝瀏覽器畫面（側欄參數 + 主區 QR 預覽）
- 「後台」＝同一行程式內的 Python 管線（融合、模擬、解碼）

因此**免費部署只要部署一個 Streamlit App**，不需另租資料庫或 API 主機（目前也沒有）。

---

## 3. 免費部署（Streamlit Community Cloud）

這是官方免費方案，適合新手，與本專案技術棧一致。

### 3.1 前置

1. 程式已推到 **公開** GitHub 倉庫  
2. 用同一個 GitHub 帳號登入 [https://share.streamlit.io](https://share.streamlit.io)（或 [https://streamlit.io/cloud](https://streamlit.io/cloud)）

### 3.2 部署步驟（約 3 分鐘）

1. 開啟 Streamlit Cloud → **New app**
2. Repository：選 `thielip/DualLayer-QR-Fusion-Engine`
3. Branch：`main`
4. Main file path：`app_ui.py`
5. 按 **Deploy**

或直接開啟一鍵連結（需已登入 Streamlit Cloud）：

https://share.streamlit.io/deploy?repository=thielip/DualLayer-QR-Fusion-Engine&branch=main&mainModule=app_ui.py
6. （可選）App settings → Secrets 貼上：

```toml
QR_ACCESS_PASSWORD = "Dual-Layer Smart QR"
```

部署完成後會得到類似：

`https://<app-name>.streamlit.app`

### 3.3 免費方案限制（需知）

- App 一段時間無人使用可能休眠，下次開啟較慢
- 資源有限，不適合高併發正式商用
- 產生的 PNG 存在**雲端實例暫時磁碟**，重啟後可能消失；重要檔請用畫面上的「下載」

### 3.4 更新上線

之後只要：

```bash
git add -A
git commit -m "..."
git push
```

Streamlit Cloud 會自動重新部署（若已連結該 repo）。

---

## 4. 其他免費備援（可選）

| 平台 | 適合 | 備註 |
|------|------|------|
| Hugging Face Spaces（Streamlit SDK） | 備援展示 | 需 HF 帳號 |
| 本機 + `start.bat` | 展示／比賽現場 | 零成本、最穩 |
| Windows `.exe` | 離線 Demo | 見 `BUILD_EXE.md`；體積大 |

無預算時建議：**GitHub 放原始碼 + Streamlit Cloud 放線上 Demo + 本機／exe 做現場演示**。

---

## 5. Git 與發佈檢查清單

推送前確認：

- [ ] `.gitignore` 排除 `output/`、`build/`、`dist/`、`release/`、`*.exe`、`SN.txt`
- [ ] 無絕對本機路徑寫死在需提交的設定
- [ ] `pytest` 通過
- [ ] README 啟動步驟可跟做
- [ ] 密碼僅以「示範閘道」描述，勿宣傳成資安功能

---

## 6. 聯絡與延伸閱讀

- 操作參數：`docs/DUAL_INFO_MANUAL.md`
- 從零復刻：`docs/DEVELOPMENT.md`
- 打包 exe：`docs/BUILD_EXE.md`
