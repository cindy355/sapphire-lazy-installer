# Sapphire 懶人安裝精靈

把 [Sapphire](https://github.com/ddxfish/sapphire)(開源、可自架、有長期記憶的 AI 陪伴框架)的安裝流程,
從「改 yml 檔案 + 打指令」變成「填表單 + 按按鈕」。全程不需要打開終端機。

> ⚠️ **目前狀態(2026-07)**
> 僅支援 **Windows**,已在一台全新安裝、原本沒裝過 Docker 的真實 Windows 機器上,
> 完整驗證過一次端到端流程(Docker 自動安裝 → 表單 → 容器啟動 → 服務就緒 → 瀏覽器自動開啟),
> 過程中發現並修正過一個 PATH 快取導致的誤判 bug。
> 目前僅在**這一台機器**上驗證過,尚未經過大量不同環境測試,也**尚未支援 Mac**。
> 如果你在其他環境使用時遇到問題,歡迎開 Issue 回報,會很有幫助。

## 使用方式

1. 確認電腦已安裝 [Python 3.9 以上版本](https://www.python.org/downloads/)(下載安裝時記得勾選「Add to PATH」)
2. 雙擊執行本程式,或在終端機打:
   ```
   python sapphire_installer.py
   ```
3. 依照畫面指示:
   - 第一步:程式會自動檢查你有沒有裝 Docker Desktop。沒裝的話,Windows 使用者可以直接點「🚀 自動下載並安裝 Docker Desktop」,不需要系統管理員權限
   - 第二步:選你要用的 AI 模型(Claude / GPT / Gemini / 本機模型),貼上 API Key
   - 第三步:按下開始,等它自動產生設定檔、啟動容器,完成後按「開啟 Sapphire」自動跳出瀏覽器

## 這個工具做了什麼(給想了解細節的人看)

- **Windows**:偵測到沒裝 Docker 時,可以一鍵下載並以 per-user 靜默模式安裝 Docker Desktop(不需要系統管理員權限)
- 幫你在 `~/sapphire` 資料夾自動產生正確的 `docker-compose.yml`
- 用你選的 AI 供應商跟 API Key,自動填好對應的環境變數
- 背景執行 `docker compose up -d`,即時把安裝過程顯示在畫面上
- 偵測服務啟動完成後自動開啟瀏覽器(注意是 `https://`,不是 `http://`,因為 Sapphire 用自簽憑證,瀏覽器會跳安全警告是正常的,點「進階」→「繼續前往」即可)

## ⚠️ 安全性提醒

`~/sapphire/docker-compose.yml` 這個檔案裡會用**明碼**存放你的 API Key。
**不要把這個檔案、這個資料夾、或裡面內容的截圖,分享或上傳給別人**,否則你的 API Key 會外洩。
這是 Sapphire 本身的設計方式,不是這個安裝精靈造成的,但提醒你留意。

## 這個工具「沒有」做的事

- **Mac**:目前完全沒有支援,沒有自動偵測、沒有自動安裝 Docker。如果你在 Mac 上想用 Sapphire,請直接參考 [Sapphire 官方安裝說明](https://github.com/ddxfish/sapphire)
- 不會修改 Sapphire 本體的任何程式碼,單純是幫你把官方的 Docker 安裝方式包裝成圖形介面
- 自動安裝完 Docker 後,**Docker Desktop 不會自動啟動**,而且第一次啟用 WSL 2 可能需要重新開機——這兩步畫面上會提示,但需要使用者自己動手完成

## 一鍵驗證(選用,用 Claude Code 實際跑一次)

如果你有裝 [Claude Code](https://docs.claude.com/en/docs/claude-code/overview),
可以雙擊 `開始驗證-Windows.bat`,它會自動把驗證任務指令複製到剪貼簿並開啟 Claude Code,
貼上(Ctrl+V)、按 Enter 即可請它幫你跑一次流程、回報卡在哪。這步純粹是額外輔助,不是必要步驟。

## 已知限制

- 目前僅在單一台 Windows 機器上做過一次完整端到端驗證,尚未經過大量不同環境(不同 Windows 版本、防毒軟體、網路環境)測試
- 尚未測試過「安裝過程中網路中斷」「防毒軟體攔截安裝檔」等異常情境
- 部分版本的 Docker 安裝程式,即使加了靜默參數仍可能跳出確認視窗(這是 Docker 官方已知問題,不是本工具的 bug),畫面上已加上對應提示
- Mac 完全未支援,詳見上方說明

## 授權

MIT License,詳見 [LICENSE](./LICENSE)。
