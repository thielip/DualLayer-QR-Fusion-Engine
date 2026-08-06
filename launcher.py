"""Windows launcher for the packaged Dual-Layer QR Fusion Engine (.exe entry point)."""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _setup_runtime() -> Path:
    """Prepare working directory and return the bundled asset root."""
    if getattr(sys, "frozen", False):
        bundle_root = Path(sys._MEIPASS)
        app_root = Path(sys.executable).parent
        os.chdir(app_root)
        (app_root / "output").mkdir(parents=True, exist_ok=True)
        return bundle_root

    app_root = Path(__file__).resolve().parent
    os.chdir(app_root)
    (app_root / "output").mkdir(parents=True, exist_ok=True)
    return app_root


def _open_browser(url: str, delay_seconds: float = 2.5) -> None:
    def _worker() -> None:
        time.sleep(delay_seconds)
        webbrowser.open(url)

    threading.Thread(target=_worker, daemon=True).start()


def main() -> int:
    bundle_root = _setup_runtime()
    app_ui = bundle_root / "app_ui.py"
    if not app_ui.exists():
        print(f"找不到 app_ui.py：{app_ui}")
        return 1

    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    host = os.environ.get("STREAMLIT_SERVER_ADDRESS", "localhost")
    url = f"http://{host}:{port}"

    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    # The frozen build runs outside the repo, so .streamlit/config.toml is not
    # discoverable; without a dark base theme the widgets stay light-on-light.
    os.environ.setdefault("STREAMLIT_THEME_BASE", "dark")
    os.environ.setdefault("STREAMLIT_THEME_PRIMARY_COLOR", "#0ea5e9")
    os.environ.setdefault("STREAMLIT_THEME_BACKGROUND_COLOR", "#0b0f17")
    os.environ.setdefault("STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR", "#121826")
    os.environ.setdefault("STREAMLIT_THEME_TEXT_COLOR", "#e8eef7")

    _open_browser(url)

    sys.argv = [
        "streamlit",
        "run",
        str(app_ui),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        f"--server.port={port}",
        f"--server.address={host}",
    ]

    from streamlit.web import cli as stcli

    return int(stcli.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
