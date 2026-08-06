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
| Cloud 部署失敗（requirements／Oh no） | 雲端套件不相容（常見於 OpenCV） | 本專案已改用 `zxing-cpp`（無需 packages.txt）。到 App 右下角 Manage app → Reboot；若仍失敗，把畫面上的紅色錯誤貼給開發者 |
| OpenCV 解碼空結果 | 圖太小或對比不足 | 提高 `final_size`／DPI 預設 |
| Streamlit 輸入看不見字 | 主題衝突 | 確認 `.streamlit/config.toml` 為 dark |
| 密碼解不開 | secrets／環境變數打錯 | 檢查 `QR_ACCESS_PASSWORD`；預設見 `.env.example` |

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

### 3.2 部署步驟（約 3 分鐘）— 新手必看

> **重要：** 日誌若出現 `Python 3.13` / `3.14`，App 常會一直「Oh no」。  
> Streamlit **不能**靠檔案改 Python 版本；已上線的 App 也**不能直接改**，必須刪掉後重新 Deploy，並在進階設定選 **3.11**。

1. 開啟 https://share.streamlit.io/ 並用 GitHub 登入  
2. 若已有失敗的 App：點右邊 **⋯** → **Delete**（刪除）  
3. 開啟：

https://share.streamlit.io/deploy?repository=thielip/DualLayer-QR-Fusion-Engine&branch=main&mainModule=app_ui.py

4. 確認 Repository / Branch=`main` / Main file=`app_ui.py`  
5. 點 **Advanced settings**（進階設定）  
6. **Python version** 選 **3.11**（不要選 3.13 / 3.14）→ **Save**  
7. 點 **Deploy**，等 2～5 分鐘  

示範密碼：`Dual-Layer Smart QR`

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
