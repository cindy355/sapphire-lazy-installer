@echo off
chcp 65001 >nul
REM 開始驗證-Windows.bat
REM 雙擊這個檔案,會自動:
REM   1. 切換到本資料夾(sapphire_installer.py 所在位置)
REM   2. 把驗證任務的指令複製到剪貼簿
REM   3. 開啟 Claude Code
REM 你只需要在 Claude Code 開啟後按 Ctrl+V 貼上、按 Enter 送出即可。

cd /d "%~dp0"

echo ======================================
echo   Sapphire 安裝精靈 - 驗證啟動器
echo ======================================
echo.
echo 目前資料夾: %cd%
echo.

where claude >nul 2>nul
if errorlevel 1 (
    echo [X] 沒有偵測到 Claude Code。
    echo.
    echo 請先前往安裝:
    echo   https://claude.ai/install.sh
    echo   或參考 https://docs.claude.com/en/docs/claude-code/overview
    echo.
    echo 安裝完成後,重新雙擊這個檔案即可。
    pause
    exit /b 1
)

echo [OK] 偵測到 Claude Code
echo.

set TASK_PROMPT=幫我在這台電腦上實際執行 sapphire_installer.py 這支程式,完整跑過一次它的四個步驟(歡迎頁、Docker 偵測、表單、安裝執行)。如果 Docker 沒有安裝或沒有啟動,請提醒我先處理好再繼續。過程中如果有任何錯誤訊息或程式卡住的地方,請截取關鍵錯誤內容給我看,並告訴我可能是哪一步出的問題,不需要自己動手改程式碼,先如實回報執行結果就好。

echo %TASK_PROMPT% | clip
echo [已複製] 驗證任務指令已複製到剪貼簿。
echo.
echo 即將開啟 Claude Code,開啟後請按 Ctrl+V 貼上、再按 Enter 送出。
echo.
timeout /t 2 >nul

claude
