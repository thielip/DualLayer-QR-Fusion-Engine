@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Dual-Layer Smart QR Fusion Engine

where py >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python。請安裝 Python 3.10 或以上版本。
    pause
    exit /b 1
)

if not exist "output\" mkdir "output"

echo.
echo ================================================
echo   Dual-Layer Smart QR Fusion Engine
echo   開發模式啟動（Streamlit 本機伺服器）
echo ================================================
echo.
echo 瀏覽器將開啟 http://localhost:8501
echo 示範閘道密碼預設：Dual-Layer Smart QR
echo （可用環境變數 QR_ACCESS_PASSWORD 覆寫）
echo.

start "" "http://localhost:8501"
py -m streamlit run app_ui.py --server.headless=true --browser.gatherUsageStats=false --server.port=8501

if errorlevel 1 (
    echo.
    echo [錯誤] 啟動失敗。請確認已執行：py -m pip install -r requirements.txt
    pause
)
