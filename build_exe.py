"""Build a Windows standalone executable for the Streamlit PoC using PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "DualLayerQR_FusionEngine.spec"
APP_NAME = "DualLayerQR_FusionEngine"


def _path_sep() -> str:
    return ";" if os.name == "nt" else ":"


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "請先安裝 PyInstaller：\n  py -m pip install pyinstaller\n"
        ) from exc


def _collect_add_data() -> list[str]:
    sep = _path_sep()
    entries = [
        (ROOT / "app_ui.py", "."),
        (ROOT / "run_poc.py", "."),
        (ROOT / "launcher.py", "."),
        (ROOT / "src", "src"),
        (ROOT / "docs", "docs"),
        (ROOT / ".streamlit", ".streamlit"),
    ]
    args: list[str] = []
    for source, target in entries:
        if source.exists():
            args.extend(["--add-data", f"{source}{sep}{target}"])
    return args


def _hidden_imports() -> list[str]:
    packages = [
        "streamlit",
        "streamlit.web",
        "streamlit.web.cli",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "altair",
        "pandas",
        "numpy",
        "PIL",
        "zxingcpp",
        "qrcode",
        "qrcode.image",
        "qrcode.image.pil",
        "click",
        "tornado",
        "watchdog",
    ]
    args: list[str] = []
    for name in packages:
        args.extend(["--hidden-import", name])
    return args


def _collect_all() -> list[str]:
    modules = ["streamlit", "altair", "PIL", "qrcode", "zxingcpp"]
    args: list[str] = []
    for name in modules:
        args.extend(["--collect-all", name])
    return args


def build(*, windowed: bool = False, clean: bool = True) -> Path:
    """Run PyInstaller and return the output executable path."""
    _ensure_pyinstaller()

    if clean:
        shutil.rmtree(DIST_DIR, ignore_errors=True)
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        if SPEC_FILE.exists():
            SPEC_FILE.unlink()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ROOT / "launcher.py"),
        "--name",
        APP_NAME,
        "--onefile",
        "--noconfirm",
        *(_collect_all()),
        *(_collect_add_data()),
        *(_hidden_imports()),
    ]
    if windowed:
        cmd.append("--windowed")
    else:
        cmd.append("--console")

    print("執行打包指令：")
    print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"找不到輸出檔：{exe_path}")

    release_dir = ROOT / "release"
    release_dir.mkdir(exist_ok=True)
    shipped = release_dir / f"{APP_NAME}.exe"
    shutil.copy2(exe_path, shipped)
    (release_dir / "output").mkdir(exist_ok=True)
    readme = release_dir / "使用說明.txt"
    readme.write_text(
        "\n".join(
            [
                "Dual-Layer Smart QR Fusion Engine（PoC 封裝版）",
                "",
                "1. 雙擊 DualLayerQR_FusionEngine.exe",
                "2. 瀏覽器會自動開啟登入畫面",
                "3. 輸入授權密碼（預設見 .env.example / 文件；可用環境變數 QR_ACCESS_PASSWORD 覆寫）",
                "4. 生成結果會寫入此資料夾旁的 output\\",
                "",
                "開發者原始碼模式：雙擊 start.bat",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\n打包完成：{shipped}")
    print(f"輸出目錄：{release_dir}")
    return shipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Windows standalone .exe")
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="隱藏主控台視窗（除錯時請勿使用）",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="保留前次 build/dist 快取",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build(windowed=args.windowed, clean=not args.no_clean)
