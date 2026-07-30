#!/usr/bin/env python3
"""
Sapphire 懶人安裝精靈
======================
把 Sapphire (github.com/ddxfish/sapphire) 的 Docker 安裝流程,
從「改 yml 檔案 + 打指令」變成「填表單 + 按按鈕」。

使用者只需要:
1. 先自行安裝好 Docker Desktop (本程式會偵測,沒裝會給下載連結)
2. 執行本程式: python3 sapphire_installer.py
3. 依照畫面填 API Key、選 LLM 供應商
4. 按下「開始安裝」,等待完成後自動開啟瀏覽器

不需要打開終端機、不需要碰 yml 檔案、不需要懂 docker compose 指令。

需求: Python 3.9+ (內建 tkinter,大多數 Python 安裝都會附帶)
"""

import os
import sys
import time
import shutil
import platform
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

# ----------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------

APP_TITLE = "Sapphire 懶人安裝精靈"
SAPPHIRE_PORT = 8073
INSTALL_DIR = Path.home() / "sapphire"
DOCKER_DOWNLOAD_URL = "https://www.docker.com/products/docker-desktop/"
# 官方直接下載連結(來源: docs.docker.com/desktop/setup/install/windows-install)
DOCKER_WIN_INSTALLER_URL = (
    "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
)
SAPPHIRE_URL = f"https://localhost:{SAPPHIRE_PORT}"

LLM_PROVIDERS = {
    "Anthropic (Claude)": {
        "env_key": "ANTHROPIC_API_KEY",
        "hint": "從 console.anthropic.com 取得 API Key",
    },
    "OpenAI (GPT)": {
        "env_key": "OPENAI_API_KEY",
        "hint": "從 platform.openai.com 取得 API Key",
    },
    "Google (Gemini)": {
        "env_key": "GOOGLE_API_KEY",
        "hint": "從 aistudio.google.com 取得 API Key",
    },
    "本機模型 (LM Studio,不需要 API Key)": {
        "env_key": None,
        "hint": "請先在本機開啟 LM Studio 並載入模型",
    },
}

# 常用時區(給不熟悉 tz database 名稱的人用白話選)
TIMEZONES = {
    "台北 / 台灣": "Asia/Taipei",
    "香港": "Asia/Hong_Kong",
    "上海 / 中國": "Asia/Shanghai",
    "東京 / 日本": "Asia/Tokyo",
    "新加坡": "Asia/Singapore",
    "美國東岸": "America/New_York",
    "美國西岸": "America/Los_Angeles",
}

DOCKER_COMPOSE_TEMPLATE = """# 由 Sapphire 懶人安裝精靈自動產生,請勿手動編輯
services:
  sapphire:
    image: ghcr.io/ddxfish/sapphire:latest
    container_name: sapphire
    restart: unless-stopped
    ports:
      - "{port}:8073"
    volumes:
      - ./sapphire-data:/app/user
      - ./sapphire-backups:/app/user_backups
      - ./sapphire-config:/home/sapphire/.config/sapphire
    environment:
      TZ: "{timezone}"
{env_lines}
    extra_hosts:
      - "host.docker.internal:host-gateway"
"""


# ----------------------------------------------------------------------
# 背景檢查 / 執行邏輯 (不碰 UI thread 以外的東西)
# ----------------------------------------------------------------------

def _resolve_docker_exe() -> str:
    """回傳可用的 docker 執行檔路徑,PATH 找不到時退回已知安裝路徑"""
    found = shutil.which("docker")
    if found:
        return found

    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop"
            / "resources" / "bin" / "docker.exe",
            Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

    return "docker"  # 找不到就照舊回傳指令名稱,讓呼叫端的錯誤處理去接手


def check_docker_installed() -> bool:
    """
    檢查 docker 指令是否存在。

    注意:剛用本精靈自動安裝完 Docker Desktop 後,Windows 會把新路徑寫進
    使用者層級 PATH(登錄檔),但「目前正在執行中的這個 Python 進程」不會
    自動重新讀取 PATH,所以 shutil.which() 在同一次執行中會誤判成「沒裝」。
    這裡額外檢查已知的實際安裝路徑作為備援,避免這種誤判。
    """
    if shutil.which("docker") is not None:
        return True

    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop"
            / "resources" / "bin" / "docker.exe",
            Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
        ]
        for c in candidates:
            if c.exists():
                return True

    return False


def check_docker_running() -> bool:
    """檢查 docker daemon 是否有在跑(用解析過的實際路徑,避免 PATH 過時誤判)"""
    try:
        docker_exe = _resolve_docker_exe()
        result = subprocess.run(
            [docker_exe, "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def download_docker_installer(dest_path: Path, log_callback):
    """從 Docker 官方下載安裝檔,回報進度給 log_callback"""
    import urllib.request

    log_callback(f"開始下載 Docker Desktop 安裝檔...")
    log_callback(f"來源: {DOCKER_WIN_INSTALLER_URL}")

    last_reported = {"pct": -10}

    def _progress(block_num, block_size, total_size):
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        pct = min(100, int(downloaded * 100 / total_size))
        # 每 10% 回報一次,避免洗版
        if pct - last_reported["pct"] >= 10:
            last_reported["pct"] = pct
            log_callback(f"下載進度: {pct}%")

    urllib.request.urlretrieve(DOCKER_WIN_INSTALLER_URL, str(dest_path), reporthook=_progress)
    log_callback("下載完成。")
    return dest_path


def install_docker_silently(installer_path: Path, log_callback) -> int:
    """
    靜默安裝 Docker Desktop(per-user 模式,不需要系統管理員權限)。
    參數依據官方文件: docs.docker.com/desktop/setup/install/windows-install
    回傳 process 的 exit code。
    """
    log_callback("開始安裝 Docker Desktop(per-user 模式,不需要管理員權限)...")
    log_callback("這一步可能需要幾分鐘,期間畫面可能沒有明顯變化,請耐心等候。")

    args = [
        str(installer_path),
        "install",
        "--quiet",
        "--accept-license",
        "--user",
        "--backend=wsl-2",
    ]
    process = subprocess.run(args, capture_output=True, text=True)

    if process.stdout:
        log_callback(process.stdout.strip())
    if process.stderr:
        log_callback(process.stderr.strip())

    return process.returncode


def write_compose_file(install_dir: Path, provider_key: str, api_key: str, timezone: str, port: int):
    """把使用者填的表單資料寫成 docker-compose.yml"""
    install_dir.mkdir(parents=True, exist_ok=True)

    env_lines = ""
    provider = LLM_PROVIDERS[provider_key]
    if provider["env_key"] and api_key.strip():
        env_lines = f'      {provider["env_key"]}: "{api_key.strip()}"'
    elif provider["env_key"] is None:
        # 本機模型: 依作業系統決定 LM Studio 的連線位置
        if platform.system() == "Linux":
            lm_url = "http://172.17.0.1:1234/v1"
        else:
            lm_url = "http://host.docker.internal:1234/v1"
        env_lines = f'      LMSTUDIO_BASE_URL: "{lm_url}"'

    content = DOCKER_COMPOSE_TEMPLATE.format(
        port=port,
        timezone=timezone,
        env_lines=env_lines,
    )

    compose_path = install_dir / "docker-compose.yml"
    compose_path.write_text(content, encoding="utf-8")
    return compose_path


# ----------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------

class SapphireInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("620x520")
        self.resizable(False, False)

        self.provider_var = tk.StringVar(value=list(LLM_PROVIDERS.keys())[0])
        self.api_key_var = tk.StringVar()
        self.timezone_var = tk.StringVar(value=list(TIMEZONES.keys())[0])
        self.port_var = tk.StringVar(value=str(SAPPHIRE_PORT))

        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill="both", expand=True)

        self.step = 0
        self.steps = [
            self.build_step_welcome,
            self.build_step_docker_check,
            self.build_step_form,
            self.build_step_install,
        ]
        self.render_step()

    # -- 通用工具 -------------------------------------------------------

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def render_step(self):
        self.clear()
        self.steps[self.step]()

    def go_next(self):
        self.step += 1
        self.render_step()

    def title_label(self, text):
        ttk.Label(self.container, text=text, font=("Helvetica", 16, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

    def body_label(self, text):
        ttk.Label(self.container, text=text, wraplength=560, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

    # -- Step 0: 歡迎頁 --------------------------------------------------

    def build_step_welcome(self):
        self.title_label("歡迎使用 Sapphire 懶人安裝精靈")
        self.body_label(
            "這個小工具會幫你把 Sapphire(一個可自架、有長期記憶的 AI 陪伴框架)"
            "裝起來,全程不需要打開終端機、不需要碰設定檔。\n\n"
            "接下來只需要三步:\n"
            "  1. 確認電腦上有 Docker\n"
            "  2. 填一下要用哪個 AI 模型、貼上你的 API Key\n"
            "  3. 按下開始,等它裝好,自動幫你開瀏覽器"
        )
        ttk.Button(self.container, text="開始 →", command=self.go_next).pack(
            anchor="e", pady=(20, 0)
        )

    # -- Step 1: Docker 檢查 ---------------------------------------------

    def build_step_docker_check(self):
        self.title_label("第一步:檢查 Docker")
        status_frame = ttk.Frame(self.container)
        status_frame.pack(fill="x", pady=10)

        self.docker_status_label = ttk.Label(status_frame, text="檢查中...")
        self.docker_status_label.pack(anchor="w")

        self.docker_next_btn = ttk.Button(
            self.container, text="下一步 →", command=self.go_next, state="disabled"
        )
        self.docker_next_btn.pack(anchor="e", pady=(20, 0))

        self.download_btn = None

        # 背景執行檢查,避免卡住畫面
        threading.Thread(target=self._run_docker_check, daemon=True).start()

    def _run_docker_check(self):
        installed = check_docker_installed()
        running = installed and check_docker_running()

        def update_ui():
            if running:
                self.docker_status_label.config(
                    text="✅ 偵測到 Docker,而且正在執行中,可以繼續下一步。"
                )
                self.docker_next_btn.config(state="normal")
            elif installed:
                self.docker_status_label.config(
                    text="⚠️ 偵測到已安裝 Docker,但目前沒有啟動。\n"
                    "請先打開 Docker Desktop 應用程式,等它完全啟動後,"
                    "再按下方「重新檢查」。"
                )
                self._add_recheck_button()
            else:
                self.docker_status_label.config(
                    text="❌ 沒有偵測到 Docker。\n\n"
                    "Sapphire 需要透過 Docker 執行。"
                )
                if platform.system() == "Windows":
                    self.docker_status_label.config(
                        text=self.docker_status_label.cget("text")
                        + "\n可以讓本精靈自動幫你下載安裝(不需要系統管理員權限),"
                        "或是自己前往官網下載。"
                    )
                    self._add_auto_install_button()
                self._add_download_button()
                self._add_recheck_button()

        self.after(0, update_ui)

    def _add_auto_install_button(self):
        ttk.Button(
            self.container,
            text="🚀 自動下載並安裝 Docker Desktop",
            command=self.build_step_docker_auto_install,
        ).pack(anchor="w", pady=(10, 0))

    def _add_download_button(self):
        if self.download_btn is None:
            self.download_btn = ttk.Button(
                self.container,
                text="前往官網手動下載 Docker Desktop",
                command=lambda: webbrowser.open(DOCKER_DOWNLOAD_URL),
            )
            self.download_btn.pack(anchor="w", pady=(10, 0))

    # -- Docker 自動安裝畫面(Windows 限定)---------------------------------

    def build_step_docker_auto_install(self):
        self.clear()
        self.title_label("正在自動安裝 Docker Desktop")
        self.body_label(
            "這會從 Docker 官方網站下載安裝檔並以 per-user 模式靜默安裝,"
            "不需要系統管理員權限、不需要你手動點擊安裝精靈。"
        )
        self.docker_install_log = scrolledtext.ScrolledText(self.container, height=14, width=72)
        self.docker_install_log.pack(fill="both", expand=True, pady=(0, 10))
        self.docker_install_log.config(state="disabled")

        self.docker_install_recheck_btn = ttk.Button(
            self.container, text="安裝完成後,點我重新檢查", command=self.build_step_docker_check,
            state="disabled",
        )
        self.docker_install_recheck_btn.pack(anchor="e")

        threading.Thread(target=self._run_docker_auto_install, daemon=True).start()

    def _docker_install_log(self, text):
        def append():
            self.docker_install_log.config(state="normal")
            self.docker_install_log.insert("end", text + "\n")
            self.docker_install_log.see("end")
            self.docker_install_log.config(state="disabled")

        self.after(0, append)

    def _run_docker_auto_install(self):
        try:
            import tempfile

            installer_path = Path(tempfile.gettempdir()) / "DockerDesktopInstaller.exe"
            download_docker_installer(installer_path, self._docker_install_log)

            returncode = install_docker_silently(installer_path, self._docker_install_log)

            if returncode == 0:
                self._docker_install_log(
                    "\n✅ 安裝程序執行完成。\n\n"
                    "⚠️ 重要:Docker Desktop 安裝後不會自動啟動,而且第一次啟用 WSL 2 "
                    "可能需要重新啟動電腦。請依序做:\n"
                    "  1. 如果系統提示重新啟動,請先重開機\n"
                    "  2. 手動打開一次「Docker Desktop」應用程式(開始選單搜尋)\n"
                    "  3. 出現服務條款時按「Accept」\n"
                    "  4. 等待 Docker Desktop 完全啟動(圖示不再轉圈)\n"
                    "  5. 回到這裡按下方「重新檢查」"
                )
            else:
                self._docker_install_log(
                    f"\n⚠️ 安裝程式回傳了非預期的結果(exit code: {returncode})。\n"
                    "有些版本的 Docker 安裝程式即使加了靜默參數,仍會跳出一個確認視窗——"
                    "如果你有看到跳出視窗,請切到那個視窗手動點擊繼續,裝完再回來按「重新檢查」。\n"
                    "如果什麼視窗都沒看到,建議改用下方「前往官網手動下載」自行安裝一次。"
                )

            def enable_recheck():
                self.docker_install_recheck_btn.config(state="normal")

            self.after(0, enable_recheck)

        except Exception as e:
            self._docker_install_log(f"\n❌ 自動安裝過程發生錯誤: {e}")
            self._docker_install_log("建議改用「前往官網手動下載」自行安裝。")

            def enable_recheck():
                self.docker_install_recheck_btn.config(state="normal")

            self.after(0, enable_recheck)

    def _add_recheck_button(self):
        if not hasattr(self, "_recheck_btn_added"):
            self._recheck_btn_added = True
            ttk.Button(
                self.container, text="重新檢查", command=self.build_step_docker_check
            ).pack(anchor="w", pady=(10, 0))

    # -- Step 2: 表單 ------------------------------------------------------

    def build_step_form(self):
        self.title_label("第二步:設定你的 AI 伴侶要用哪個大腦")

        ttk.Label(self.container, text="選擇 LLM 供應商:").pack(anchor="w")
        provider_menu = ttk.Combobox(
            self.container,
            textvariable=self.provider_var,
            values=list(LLM_PROVIDERS.keys()),
            state="readonly",
            width=45,
        )
        provider_menu.pack(anchor="w", pady=(0, 10))
        provider_menu.bind("<<ComboboxSelected>>", lambda e: self._refresh_hint())

        self.hint_label = ttk.Label(self.container, text="", foreground="#666666")
        self.hint_label.pack(anchor="w", pady=(0, 10))
        self._refresh_hint()

        ttk.Label(self.container, text="貼上 API Key(本機模型可留空):").pack(anchor="w")
        ttk.Entry(self.container, textvariable=self.api_key_var, width=50, show="*").pack(
            anchor="w", pady=(0, 15)
        )

        ttk.Label(self.container, text="你所在的時區:").pack(anchor="w")
        ttk.Combobox(
            self.container,
            textvariable=self.timezone_var,
            values=list(TIMEZONES.keys()),
            state="readonly",
            width=45,
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(self.container, text="本機瀏覽器連接埠(不確定就不要改):").pack(anchor="w")
        ttk.Entry(self.container, textvariable=self.port_var, width=10).pack(
            anchor="w", pady=(0, 15)
        )

        ttk.Button(self.container, text="下一步 →", command=self._validate_and_next).pack(
            anchor="e", pady=(10, 0)
        )

    def _refresh_hint(self):
        provider = LLM_PROVIDERS[self.provider_var.get()]
        self.hint_label.config(text=provider["hint"])

    def _validate_and_next(self):
        provider = LLM_PROVIDERS[self.provider_var.get()]
        if provider["env_key"] and not self.api_key_var.get().strip():
            messagebox.showwarning(
                APP_TITLE, "請填入 API Key,或是改選「本機模型」選項。"
            )
            return
        try:
            int(self.port_var.get())
        except ValueError:
            messagebox.showwarning(APP_TITLE, "連接埠請填數字。")
            return
        self.go_next()

    # -- Step 3: 安裝執行 ---------------------------------------------------

    def build_step_install(self):
        self.title_label("第三步:自動安裝中")
        self.log_box = scrolledtext.ScrolledText(self.container, height=18, width=72)
        self.log_box.pack(fill="both", expand=True, pady=(0, 10))
        self.log_box.config(state="disabled")

        self.open_btn = ttk.Button(
            self.container, text="開啟 Sapphire", command=self._open_browser, state="disabled"
        )
        self.open_btn.pack(anchor="e")

        threading.Thread(target=self._run_install, daemon=True).start()

    def _log(self, text):
        def append():
            self.log_box.config(state="normal")
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")

        self.after(0, append)

    def _run_install(self):
        try:
            self._log(f"安裝資料夾: {INSTALL_DIR}")
            timezone = TIMEZONES[self.timezone_var.get()]
            port = int(self.port_var.get())

            compose_path = write_compose_file(
                INSTALL_DIR,
                self.provider_var.get(),
                self.api_key_var.get(),
                timezone,
                port,
            )
            self._log(f"已產生設定檔: {compose_path}")
            self._log("正在啟動 Sapphire(第一次啟動要下載映像檔,可能需要幾分鐘,請耐心等候)...\n")

            docker_exe = _resolve_docker_exe()
            process = subprocess.Popen(
                [docker_exe, "compose", "up", "-d"],
                cwd=str(INSTALL_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in process.stdout:
                self._log(line.rstrip())
            process.wait()

            if process.returncode != 0:
                self._log("\n❌ 啟動失敗,請把上面的錯誤訊息截圖給協助你的人看。")
                return

            self._log("\n⏳ 容器已啟動,等待服務就緒...")
            self._wait_for_service(port)
            self._log(f"\n✅ 安裝完成!Sapphire 正在 {SAPPHIRE_URL.replace(str(SAPPHIRE_PORT), str(port))} 執行。")
            self._log("按下方「開啟 Sapphire」按鈕,第一次進去會有設定精靈引導你選人設。")

            def enable_button():
                self.open_btn.config(state="normal")

            self.after(0, enable_button)

        except FileNotFoundError:
            self._log("❌ 找不到 docker 指令,請確認 Docker Desktop 已安裝並啟動。")
        except Exception as e:
            self._log(f"❌ 發生未預期的錯誤: {e}")

    def _wait_for_service(self, port, timeout=90):
        import socket

        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection(("localhost", port), timeout=2):
                    return True
            except OSError:
                time.sleep(2)
        self._log("(服務啟動比預期久,若稍後打不開,請再等一下重新整理瀏覽器)")
        return False

    def _open_browser(self):
        port = self.port_var.get()
        webbrowser.open(f"https://localhost:{port}")


if __name__ == "__main__":
    app = SapphireInstaller()
    app.mainloop()
