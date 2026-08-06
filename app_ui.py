"""Streamlit UI for dual-layer QR fusion PoC — competition-ready product prototype."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import streamlit as st

# Demo gate only — not real security. Override via QR_ACCESS_PASSWORD / Streamlit secrets.
_DEFAULT_ACCESS_PASSWORD = "Dual-Layer Smart QR"
SESSION_AUTH_KEY = "auth_unlocked"
SESSION_AUTH_ATTEMPT_KEY = "auth_attempted"


def get_access_password() -> str:
    """Resolve gate password from env, Streamlit secrets, or demo default."""
    env_value = os.environ.get("QR_ACCESS_PASSWORD", "").strip()
    if env_value:
        return env_value
    try:
        secret = st.secrets.get("QR_ACCESS_PASSWORD", "")
        if isinstance(secret, str) and secret.strip():
            return secret.strip()
    except Exception:
        pass
    return _DEFAULT_ACCESS_PASSWORD


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_bundle_root() -> Path:
    """Return the directory that contains bundled source assets."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_project_root() -> Path:
    """Return the writable working directory (next to .exe when frozen)."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BUNDLE_ROOT = get_bundle_root()
PROJECT_ROOT = get_project_root()
SRC_DIR = BUNDLE_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(1, str(BUNDLE_ROOT))

from config import (  # noqa: E402
    ALLOWED_DPI_VALUES,
    AppConfig,
    DEFAULT_CENTROID_SIZE,
    DEFAULT_DPI,
    DEFAULT_FINAL_SIZE,
    DEFAULT_MODULE_BLOCK_SIZE,
    DEFAULT_PHYSICAL_SIZE_MM,
    DistanceProfile,
    FINAL_SIZE_STEP,
    MAX_FINAL_SIZE,
    MIN_FINAL_SIZE,
    OUTPUT_PRESET_MANUAL,
    OUTPUT_PRESETS,
    apply_output_preset,
    load_default_config,
)
from run_poc import configure_logging, run_pipeline  # noqa: E402
from validator import QRDecoder  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "output"
FUSED_IMAGE = OUTPUT_DIR / "fused_qr.png"
FUSED_NEAR_IMAGE = OUTPUT_DIR / "fused_qr_near.png"
FAR_SIMULATION = OUTPUT_DIR / "simulation_far.png"
NEAR_SIMULATION = OUTPUT_DIR / "simulation_near.png"
VALIDATION_REPORT = OUTPUT_DIR / "validation_report.json"

DEFAULT_URL_A = "https://verify.yourbrand.com/marketing/001"
DEFAULT_URL_B = "https://verify.yourbrand.com/secure/token-001"
OUTPUT_PRESET_OPTIONS = [(preset.id, preset.label) for preset in OUTPUT_PRESETS] + [
    (OUTPUT_PRESET_MANUAL, "手動模式（自訂全部參數）"),
]
DPI_LABELS = {
    300: "300（一般列印）",
    600: "600（預設）",
    1200: "1200（中高解析）",
    2400: "2400（高解析列印）",
}


@dataclass
class LayerDecodeResult:
    """Result of decoding a simulation image for one layer."""

    label: str
    success: bool
    expected: str
    matched: str | None
    all_payloads: list[str]
    image_exists: bool


def inject_auth_gate_css() -> None:
    """Hide sidebar and center the login gate."""
    st.markdown(
        """
<style>
section[data-testid="stSidebar"] { display: none !important; }
section[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.block-container { max-width: 520px !important; padding-top: 12vh !important; }

.auth-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
}

.auth-card {
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
  padding: 2.25rem 2rem 2rem;
  border-radius: 20px;
  border: 1px solid rgba(56, 189, 248, 0.28);
  background: linear-gradient(160deg, rgba(18, 24, 38, 0.96) 0%, rgba(11, 15, 23, 0.98) 100%);
  box-shadow: 0 24px 80px rgba(2, 8, 23, 0.55), 0 0 0 1px rgba(148, 163, 184, 0.06) inset;
}

.auth-badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7dd3fc;
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.25);
  margin-bottom: 1rem;
}

.auth-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  color: #f8fafc;
}

.auth-sub {
  color: #94a3b8;
  margin: 0 0 1.5rem 0;
  line-height: 1.6;
}

.auth-hint {
  margin-top: 1.25rem;
  font-size: 0.82rem;
  color: #64748b;
  text-align: center;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_auth_gate() -> None:
    """Render the password gate; blocks the main UI until unlocked."""
    inject_custom_css()
    inject_auth_gate_css()

    st.markdown(
        """
<div class="auth-shell">
  <div class="auth-card">
    <span class="auth-badge">Secure Access</span>
    <p class="auth-title">核心防偽引擎存取驗證</p>
    <p class="auth-sub">
      Dual-Layer Smart QR Fusion Engine 已進入 PoC 封裝模式。<br>
      請輸入授權密碼以解鎖完整測試介面。
    </p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input(
        "授權密碼",
        type="password",
        placeholder="請輸入存取密碼",
        key="auth_password_input",
        label_visibility="collapsed",
    )

    if st.button("驗證解鎖", type="primary", use_container_width=True, key="auth_submit"):
        st.session_state[SESSION_AUTH_ATTEMPT_KEY] = True
        if not password.strip():
            st.warning("請輸入密碼後再進行驗證。")
            return
        if password == get_access_password():
            st.session_state[SESSION_AUTH_KEY] = True
            st.session_state["auth_welcome"] = True
            st.session_state.pop(SESSION_AUTH_ATTEMPT_KEY, None)
            st.rerun()
        else:
            st.error("密碼錯誤，拒絕存取核心防偽引擎")

    elif st.session_state.get(SESSION_AUTH_ATTEMPT_KEY) and not password.strip():
        st.warning("請輸入密碼後再進行驗證。")

    st.markdown(
        '<p class="auth-hint">PoC 封裝版 · 未授權存取將被阻擋</p>',
        unsafe_allow_html=True,
    )


def inject_custom_css() -> None:
    """Inject dark-tech theme and responsive layout styles."""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg-deep: #0b0f17;
  --bg-card: #121826;
  --bg-card-hover: #161f30;
  --border: rgba(99, 179, 237, 0.18);
  --accent: #38bdf8;
  --accent-strong: #0ea5e9;
  --accent-glow: rgba(56, 189, 248, 0.35);
  --text: #e8eef7;
  --text-muted: #94a3b8;
  --success: #22c55e;
  --success-bg: rgba(34, 197, 94, 0.12);
  --danger: #ef4444;
  --danger-bg: rgba(239, 68, 68, 0.12);
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
}

.stApp {
  background: radial-gradient(1200px 600px at 10% -10%, rgba(14, 165, 233, 0.12), transparent 55%),
              radial-gradient(900px 500px at 100% 0%, rgba(99, 102, 241, 0.10), transparent 50%),
              var(--bg-deep);
  color: var(--text);
}

.block-container {
  padding-top: 2rem !important;
  padding-bottom: 3.5rem !important;
  padding-left: 2.25rem !important;
  padding-right: 2.25rem !important;
  max-width: 1180px;
}

/* Main content vertical rhythm */
.main .block-container > div {
  gap: 0.35rem;
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f1522 0%, #0b1019 100%);
  border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] > div:first-child {
  padding: 1.35rem 1.1rem 2rem 1.1rem !important;
}

section[data-testid="stSidebar"] .block-container {
  padding-top: 0.5rem;
  padding-left: 0.35rem;
  padding-right: 0.35rem;
}

/* Sidebar widget spacing — less cramped */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
  margin-bottom: 0.15rem;
}

section[data-testid="stSidebar"] div[data-testid="stTextInput"],
section[data-testid="stSidebar"] div[data-testid="stSelectbox"],
section[data-testid="stSidebar"] div[data-testid="stSlider"],
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] {
  margin-bottom: 0.55rem;
}

section[data-testid="stSidebar"] hr {
  margin: 1rem 0;
  border-color: rgba(148, 163, 184, 0.18);
}

/* ── Sidebar readability ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
  color: #f1f5f9 !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  color: #ffffff !important;
  font-weight: 700 !important;
}

section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] label p {
  color: #e2e8f0 !important;
  font-weight: 600 !important;
  font-size: 0.92rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input {
  background: #1e293b !important;
  color: #f8fafc !important;
  border: 1px solid rgba(148, 163, 184, 0.45) !important;
  caret-color: #38bdf8 !important;
}

section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
  color: #94a3b8 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
  background: #1e293b !important;
  color: #f8fafc !important;
  border-color: rgba(148, 163, 184, 0.45) !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
  color: #e2e8f0 !important;
  fill: #e2e8f0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stSlider"] label p,
section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stTickBarMin"],
section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stTickBarMax"],
section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stThumbValue"] {
  color: #cbd5e1 !important;
}

section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stThumbValue"] {
  background: #0ea5e9 !important;
  color: #ffffff !important;
  border-radius: 6px !important;
  padding: 0.1rem 0.45rem !important;
}

section[data-testid="stSidebar"] .card-title {
  color: #7dd3fc !important;
}

section[data-testid="stSidebar"] .card {
  background: rgba(30, 41, 59, 0.55) !important;
  border-color: rgba(125, 211, 252, 0.25) !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
  font-size: 1rem !important;
}

.print-ready-banner {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.18) 0%, rgba(234, 88, 12, 0.12) 100%);
  border: 1px solid rgba(251, 191, 36, 0.45);
  border-radius: 14px;
  padding: 1.15rem 1.35rem;
  margin-bottom: 1.35rem;
}

.print-ready-title {
  color: #fcd34d;
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.35rem 0;
}

.print-ready-sub {
  color: #fde68a;
  font-size: 0.88rem;
  margin: 0;
  line-height: 1.5;
}

.print-tag {
  display: inline-block;
  background: rgba(245, 158, 11, 0.25);
  border: 1px solid rgba(251, 191, 36, 0.5);
  color: #fef3c7;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  margin-bottom: 0.5rem;
}

.hero-wrap {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.14) 0%, rgba(99, 102, 241, 0.10) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 1.65rem 2rem;
  margin-bottom: 1.75rem;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.hero-title {
  font-size: clamp(1.35rem, 3vw, 2rem);
  font-weight: 700;
  margin: 0 0 0.35rem 0;
  background: linear-gradient(90deg, #e2e8f0 0%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-sub {
  color: var(--text-muted);
  font-size: clamp(0.85rem, 2vw, 0.98rem);
  margin: 0;
  line-height: 1.55;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.15rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
}

.card-title {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 0.75rem;
}

/* QR / preview images: fixed display size, centered */
div[data-testid="stImage"],
div[data-testid="stImageContainer"] {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
}

div[data-testid="stImage"] img {
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
  background: #fff;
  max-width: 280px !important;
  height: auto !important;
}

div[data-testid="stImage"] [data-testid="stImageCaption"],
div[data-testid="stImage"] figcaption,
div[data-testid="stCaptionContainer"] {
  text-align: center !important;
  max-width: 320px;
  color: var(--text-muted) !important;
}

.panel-section {
  margin-top: 0.5rem;
  margin-bottom: 1.25rem;
}

.sidebar-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 1rem 0;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1.15rem;
}

.decode-card {
  border-radius: 14px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.75rem;
  border: 1px solid transparent;
}

.decode-card.success {
  background: var(--success-bg);
  border-color: rgba(34, 197, 94, 0.35);
}

.decode-card.fail {
  background: var(--danger-bg);
  border-color: rgba(239, 68, 68, 0.35);
}

.decode-status {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.35rem 0;
}

.decode-status.ok { color: var(--success); }
.decode-status.bad { color: var(--danger); }

.decode-url {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  word-break: break-all;
  color: var(--text);
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  margin-top: 0.45rem;
}

.meta-pill {
  display: inline-block;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.25);
  color: #bae6fd;
  font-size: 0.78rem;
  margin-right: 0.35rem;
  margin-bottom: 0.35rem;
}

div[data-testid="stButton"] > button {
  border-radius: 12px !important;
  font-weight: 600 !important;
  padding: 0.65rem 1rem !important;
  border: 1px solid rgba(56, 189, 248, 0.35) !important;
  transition: all 0.2s ease !important;
}

div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%) !important;
  color: white !important;
  box-shadow: 0 8px 24px var(--accent-glow) !important;
}

div[data-testid="stButton"] > button[kind="secondary"] {
  background: rgba(255, 255, 255, 0.04) !important;
  color: var(--text) !important;
}

/* Streamlit >=1.60 wraps inputs in stTextInputRootElement, which keeps the
   light-theme background and hides light-on-light text and caret. */
div[data-testid="stTextInputRootElement"],
div[data-testid="stNumberInputContainer"] {
  background: rgba(255, 255, 255, 0.04) !important;
  border-color: var(--border) !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
  border-radius: 10px !important;
  background: transparent !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
  caret-color: var(--accent) !important;
}

div[data-testid="stTextInput"] input::placeholder {
  color: var(--text-muted) !important;
}

section[data-testid="stSidebar"] div[data-testid="stTextInputRootElement"],
section[data-testid="stSidebar"] div[data-testid="stNumberInputContainer"] {
  background: #1e293b !important;
  border-color: rgba(148, 163, 184, 0.45) !important;
}

section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] {
  background: transparent !important;
  color: #f8fafc !important;
  border-color: rgba(148, 163, 184, 0.45) !important;
}

div[data-testid="stSlider"] [data-baseweb="slider"] div {
  border-radius: 999px !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.5rem;
}

.stTabs [data-baseweb="tab"] {
  border-radius: 10px 10px 0 0;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  padding: 0.5rem 1rem;
}

@media (max-width: 900px) {
  .block-container {
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
  }
  div[data-testid="column"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  .hero-wrap { padding: 1.2rem 1.1rem; }
  div[data-testid="stImage"] img {
    max-width: 240px !important;
  }
}

@media (max-width: 640px) {
  section[data-testid="stSidebar"] {
    min-width: 100% !important;
    max-width: 100% !important;
  }
}

/* Tabs breathing room */
.stTabs [data-baseweb="tab-panel"] {
  padding-top: 1.15rem;
}

div[data-testid="stHorizontalBlock"] {
  gap: 1rem !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def build_config_from_ui(
    *,
    url_a: str,
    url_b: str,
    output_preset: str,
    module_block_size: int | None,
    centroid_size: int | None,
    final_size: int,
    dpi: int,
    physical_size_mm: float,
) -> AppConfig:
    """Build backend AppConfig from UI inputs."""
    config = load_default_config()
    config.url_a = url_a.strip()
    config.url_b = url_b.strip()
    config.output_dir = str(OUTPUT_DIR)
    apply_output_preset(config, output_preset)

    if output_preset == OUTPUT_PRESET_MANUAL:
        config.render.final_size = int(final_size)
        config.render.dpi = int(dpi)
        config.render.physical_size_mm = float(physical_size_mm)
        config.fusion.module_block_size = module_block_size
        config.fusion.centroid_size = centroid_size
        config.fusion.auto_tune = False

    return config


def load_validation_report() -> dict | None:
    """Load validation_report.json if it exists."""
    if not VALIDATION_REPORT.exists():
        return None
    return json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))


def _match_payload(decoded_values: list[str], expected: str) -> tuple[bool, str | None]:
    for value in decoded_values:
        if value == expected or expected in value or value in expected:
            return True, value
    return False, None


def _match_payload_b(decoded_values: list[str], expected_b: str, expected_a: str) -> tuple[bool, str | None]:
    for value in decoded_values:
        if value and (value == expected_a or expected_a in value or value in expected_a):
            continue
        if value == expected_b or expected_b in value or value in expected_b:
            return True, value
    return False, None


def _read_gray_image(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    return image


def decode_image_file(
    *,
    image_path: Path,
    expected: str,
    label: str,
    profile: DistanceProfile | None = None,
    other_url: str | None = None,
) -> LayerDecodeResult:
    """Decode an output PNG using OpenCV QRCodeDetector."""
    image = _read_gray_image(image_path)
    if image is None:
        return LayerDecodeResult(
            label=label,
            success=False,
            expected=expected,
            matched=None,
            all_payloads=[],
            image_exists=False,
        )

    decoder = QRDecoder()
    payloads: list[str] = []
    seen: set[str] = set()

    def extend(values: list[str]) -> None:
        for value in values:
            if value and value not in seen:
                seen.add(value)
                payloads.append(value)

    profiles = [profile] if profile is not None else [DistanceProfile.FAR, DistanceProfile.NEAR]
    for active in profiles:
        extend(decoder.decode_with_retries(image, active))

    if other_url is not None:
        success, matched = _match_payload_b(payloads, expected, other_url)
    else:
        success, matched = _match_payload(payloads, expected)

    return LayerDecodeResult(
        label=label,
        success=success,
        expected=expected,
        matched=matched,
        all_payloads=payloads,
        image_exists=True,
    )


def _output_paths(output_dir: Path | None = None) -> dict[str, Path]:
    base = output_dir or OUTPUT_DIR
    return {
        "fused": base / "fused_qr.png",
        "fused_near": base / "fused_qr_near.png",
        "far_sim": base / "simulation_far.png",
        "near_sim": base / "simulation_near.png",
    }


def run_decode_test(
    *,
    expected_a: str,
    expected_b: str,
    output_dir: Path | None = None,
) -> dict[str, LayerDecodeResult]:
    """Decode output images; primary artifact is the single fused_qr.png."""
    paths = _output_paths(output_dir)
    base = output_dir or OUTPUT_DIR
    fused = paths["fused"]

    def decode_fused_far() -> LayerDecodeResult:
        return decode_image_file(
            image_path=fused,
            expected=expected_a,
            label="融合定稿 · 遠掃（網址 A）",
            profile=DistanceProfile.FAR,
        )

    def decode_fused_near() -> LayerDecodeResult:
        payloads: list[str] = []
        seen: set[str] = set()

        def extend(values: list[str]) -> None:
            for value in values:
                if value and value not in seen:
                    seen.add(value)
                    payloads.append(value)

        near_ref = paths["fused_near"]
        recovered_b = base / "recovered_layer_b.png"
        for ref_path in (near_ref, recovered_b):
            if ref_path.exists():
                extend(
                    decode_image_file(
                        image_path=ref_path,
                        expected=expected_b,
                        label="",
                        profile=DistanceProfile.NEAR,
                        other_url=expected_a,
                    ).all_payloads,
                )

        if fused.exists():
            extend(
                decode_image_file(
                    image_path=fused,
                    expected=expected_b,
                    label="",
                    profile=DistanceProfile.NEAR,
                    other_url=expected_a,
                ).all_payloads,
            )

        success, matched = _match_payload_b(payloads, expected_b, expected_a)
        return LayerDecodeResult(
            label="融合定稿 · 近掃（網址 B）",
            success=success,
            expected=expected_b,
            matched=matched,
            all_payloads=payloads,
            image_exists=fused.exists(),
        )

    fused_far = decode_fused_far()
    fused_near = decode_fused_near()
    return {
        "far": decode_image_file(
            image_path=paths["far_sim"],
            expected=expected_a,
            label="模擬遠掃（QR-A）",
            profile=DistanceProfile.FAR,
        ),
        "near": decode_image_file(
            image_path=paths["near_sim"],
            expected=expected_b,
            label="模擬近掃（QR-B）",
            profile=DistanceProfile.NEAR,
            other_url=expected_a,
        ),
        "fused_far": fused_far,
        "fused_near": fused_near,
        # Aliases kept for older tests / callers
        "far_direct": fused_far,
        "near_direct": fused_near,
    }


def render_centered_qr_image(
    image_path: Path,
    *,
    caption: str,
    width: int = 280,
) -> None:
    """Show a QR preview at a fixed width, centered in the content column."""
    _left, mid, _right = st.columns([1.2, 1, 1.2])
    with mid:
        st.image(str(image_path), caption=caption, width=width)


def render_centered_sim_image(image_path: Path, *, caption: str, width: int = 200) -> None:
    """Show a simulation preview image at a modest fixed size."""
    st.image(str(image_path), caption=caption, width=width)


def render_decode_card(result: LayerDecodeResult) -> None:
    """Render a green/red decode status card."""
    css_class = "success" if result.success else "fail"
    status_class = "ok" if result.success else "bad"
    status_text = "解碼成功" if result.success else "解碼失敗"

    if not result.image_exists:
        st.markdown(
            f"""
<div class="decode-card fail">
  <p class="decode-status bad">{result.label} · 找不到圖檔</p>
  <p style="color:var(--text-muted);margin:0;">請先生成 QR Code 或確認 output 目錄存在模擬圖。</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        return

    matched = result.matched or "—"
    st.markdown(
        f"""
<div class="decode-card {css_class}">
  <p class="decode-status {status_class}">{result.label} · {status_text}</p>
  <p style="color:var(--text-muted);margin:0 0 0.25rem 0;">預期網址</p>
  <div class="decode-url">{result.expected}</div>
  <p style="color:var(--text-muted);margin:0.75rem 0 0.25rem 0;">解碼結果</p>
  <div class="decode-url">{matched}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_decode_tester(*, auto_run: bool = False) -> None:
    """Render the AI barcode decode test panel."""
    params = st.session_state.get("last_run_params", {})
    expected_a = params.get("url_a", DEFAULT_URL_A)
    expected_b = params.get("url_b", DEFAULT_URL_B)

    st.markdown('<div class="card"><div class="card-title">AI 條碼讀取還原引擎</div>', unsafe_allow_html=True)
    st.caption("OpenCV QRCodeDetector · 模擬圖 + 實機輸出圖雙重驗證。")

    manual = st.button("手動觸發解碼測試", type="secondary", use_container_width=True, key="manual_decode")

    if auto_run or manual or "decode_results" not in st.session_state:
        if FUSED_IMAGE.exists() or FAR_SIMULATION.exists() or manual or auto_run:
            with st.spinner("正在分析解碼結果…"):
                st.session_state["decode_results"] = run_decode_test(
                    expected_a=expected_a,
                    expected_b=expected_b,
                )

    results: dict[str, LayerDecodeResult] | None = st.session_state.get("decode_results")
    if results is None:
        st.info("尚無解碼資料。請先生成 QR Code 或點擊「手動觸發解碼測試」。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("**融合定稿解碼（同一張 QR Code）**")
    col_fused_far, col_fused_near = st.columns(2, gap="large")
    with col_fused_far:
        render_decode_card(results["fused_far"])
    with col_fused_near:
        render_decode_card(results["fused_near"])

    st.markdown("**模擬光學解碼（參考）**")
    col_far, col_near = st.columns(2, gap="large")
    with col_far:
        render_decode_card(results["far"])
    with col_near:
        render_decode_card(results["near"])

    fused_ok = results["fused_far"].success and results["fused_near"].success
    if fused_ok:
        st.success("同一張融合 QR Code 已通過遠掃 A / 近掃 B 解碼驗證，可送印 fused_qr.png。")
    elif results["fused_far"].success:
        st.warning("遠掃 A 通過；近掃 B 未通過，可嘗試調小 Centroid Size (ω) 或換用手動模式微調參數。")
    elif results["fused_near"].success:
        st.warning("近掃 B 通過；遠掃 A 未通過，請調整參數後重新生成。")
    else:
        st.error("融合定稿解碼未通過，請調整參數後重新生成。")

    st.markdown("</div>", unsafe_allow_html=True)


def render_results() -> None:
    """Render generated artifacts in the main panel."""
    report = load_validation_report()

    if report is not None:
        pills = (
            f'<div class="meta-row">'
            f'<span class="meta-pill">final_size {report.get("final_size", "—")} px</span>'
            f'<span class="meta-pill">DPI {report.get("dpi", "—")}</span>'
            f'<span class="meta-pill">'
            f'{report.get("output_pixel_width", "—")}×{report.get("output_pixel_height", "—")} px'
            f"</span>"
        )
        if report.get("qr_version"):
            pills += f'<span class="meta-pill">QR v{report["qr_version"]}</span>'
        pills += "</div>"
        st.markdown(pills, unsafe_allow_html=True)

    tab_output, tab_sim, tab_report = st.tabs(["融合輸出", "模擬掃描", "驗證報告"])

    with tab_output:
        st.markdown('<div class="card panel-section">', unsafe_allow_html=True)
        st.markdown("**最終融合 QR Code（單一輸出）**")
        st.caption("同一張圖：遠距離（約 30 cm 以上）掃描 → 網址 A｜近距離（約 5–10 cm）掃描 → 網址 B")
        if FUSED_IMAGE.exists():
            render_centered_qr_image(
                FUSED_IMAGE,
                caption="fused_qr.png — 雙層融合定稿（唯一印刷檔）",
            )
            dl_left, dl_mid, dl_right = st.columns([1, 1.4, 1])
            with dl_mid:
                st.download_button(
                    label="下載 fused_qr.png（印刷定稿）",
                    data=FUSED_IMAGE.read_bytes(),
                    file_name="fused_qr.png",
                    mime="image/png",
                    use_container_width=True,
                    key="dl_output_fused",
                )
        else:
            st.warning("找不到 fused_qr.png，請先生成。")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_sim:
        st.markdown('<div class="card panel-section">', unsafe_allow_html=True)
        st.markdown("**模擬掃描預覽**")
        st.caption("左：遠距離光學模擬｜右：近距離 QR-B 圖層模擬（非實機近掃用圖）")
        col_far, col_near = st.columns(2, gap="large")
        with col_far:
            if FAR_SIMULATION.exists():
                render_centered_sim_image(FAR_SIMULATION, caption="simulation_far.png")
            else:
                st.info("尚無 simulation_far.png")
        with col_near:
            if NEAR_SIMULATION.exists():
                render_centered_sim_image(NEAR_SIMULATION, caption="simulation_near.png")
            else:
                st.info("尚無 simulation_near.png")
        st.markdown("</div>", unsafe_allow_html=True)

        render_decode_tester(auto_run=st.session_state.get("auto_decode", False))
        st.session_state["auto_decode"] = False

    with tab_report:
        st.markdown(
            """
<div class="print-ready-banner">
  <p class="print-ready-title">📦 最終融合 QR Code · 印刷定稿</p>
  <p class="print-ready-sub">
    以下為<strong>唯一</strong>送印用圖檔 <code>fused_qr.png</code>。
    同一張 QR Code：遠掃解讀<strong>網址 A</strong>，近掃解讀<strong>網址 B</strong>。
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )

        if FUSED_IMAGE.exists():
            st.markdown('<span class="print-tag">Final · 雙層融合定稿</span>', unsafe_allow_html=True)
            render_centered_qr_image(
                FUSED_IMAGE,
                caption="fused_qr.png — 遠掃 A / 近掃 B（請送印此檔）",
            )
            dl_col, info_col = st.columns([1, 2], gap="large")
            with dl_col:
                st.download_button(
                    label="⬇ 下載印刷定稿",
                    data=FUSED_IMAGE.read_bytes(),
                    file_name="fused_qr.png",
                    mime="image/png",
                    use_container_width=True,
                    key="dl_report_fused",
                )
            with info_col:
                params = st.session_state.get("last_run_params", {})
                url_a = params.get("url_a", report.get("decoded_qr_a", "—") if report else "—")
                url_b = params.get("url_b", report.get("decoded_qr_b", "—") if report else "—")
                st.markdown(
                    f"""
<div class="card" style="margin-bottom:0;">
  <div class="card-title">雙層 Payload</div>
  <p style="margin:0.25rem 0;color:#94a3b8;font-size:0.85rem;">遠掃（網址 A）</p>
  <div class="decode-url">{url_a}</div>
  <p style="margin:0.75rem 0 0.25rem;color:#94a3b8;font-size:0.85rem;">近掃（網址 B）</p>
  <div class="decode-url">{url_b}</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.warning("尚無 fused_qr.png，請先生成。")

        decode_results = st.session_state.get("decode_results")
        if decode_results is not None:
            st.markdown("**定稿解碼驗證（同一張圖）**")
            dc1, dc2 = st.columns(2, gap="large")
            with dc1:
                render_decode_card(decode_results["fused_far"])
            with dc2:
                render_decode_card(decode_results["fused_near"])

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">驗證摘要</div>', unsafe_allow_html=True)
        if report is not None:
            detected_a = report.get("qr_a_detected", False)
            detected_b = report.get("qr_b_detected", False)
            direct_a = report.get("qr_a_direct_scan", False)
            near_b = report.get("qr_b_near_scan", False)

            summary_cols = st.columns(4, gap="medium")
            summary_cols[0].metric("QR-A 驗證", "通過" if detected_a else "未通過")
            summary_cols[1].metric("QR-B 驗證", "通過" if detected_b else "未通過")
            summary_cols[2].metric("遠掃直接解碼", "通過" if direct_a else "未通過")
            summary_cols[3].metric("近掃直接解碼", "通過" if near_b else "未通過")

            if direct_a and detected_b:
                st.success("融合定稿 fused_qr.png 驗證通過，可送印。")
            elif direct_a:
                st.warning("遠掃 A 通過；建議調整參數以強化近掃 B。")
            else:
                st.error("定稿尚未通過驗證，請調整參數後重新生成。")

            with st.expander("完整 validation_report.json", expanded=False):
                st.json(report)
            with st.expander("技術參考：B 圖層還原預覽（非送印檔）", expanded=False):
                if FUSED_NEAR_IMAGE.exists():
                    render_centered_sim_image(
                        FUSED_NEAR_IMAGE,
                        caption="fused_qr_near.png（內部 B 圖層還原，僅供除錯）",
                        width=220,
                    )
                else:
                    st.caption("尚無還原預覽。")
        else:
            st.info("尚無 validation_report.json")
        st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar_controls() -> tuple[str, str, str, int | None, int | None, int, int, float, bool]:
    """Render styled sidebar controls and return input values."""
    st.markdown(
        """
<div class="card" style="margin-top:0;">
  <div class="card-title">Payload 設定</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    url_a = st.text_input(
        "網址 A（遠掃）",
        value=DEFAULT_URL_A,
        help="遠距離掃描時讀取的 URL（QR-A）。",
    )
    url_b = st.text_input(
        "網址 B（近掃）",
        value=DEFAULT_URL_B,
        help="近距離掃描時讀取的 URL（QR-B）。",
    )

    st.markdown('<div style="height:0.55rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title">輸出預設</div>', unsafe_allow_html=True)
    preset_ids = [item[0] for item in OUTPUT_PRESET_OPTIONS]
    preset_labels = {item[0]: item[1] for item in OUTPUT_PRESET_OPTIONS}
    output_preset = st.selectbox(
        "輸出參數預設",
        options=preset_ids,
        index=preset_ids.index("a4_print"),
        format_func=lambda value: preset_labels[value],
        help="四種常用場景預設；選「手動模式」可自訂全部參數。詳見 docs/DUAL_INFO_MANUAL.md",
    )

    selected = next(p for p in OUTPUT_PRESETS if p.id == output_preset) if output_preset != OUTPUT_PRESET_MANUAL else None

    if output_preset == OUTPUT_PRESET_MANUAL:
        st.caption("手動模式：以下參數皆可在前台調整。")
        final_size = st.slider(
            "Final Size（px）",
            min_value=MIN_FINAL_SIZE,
            max_value=MAX_FINAL_SIZE,
            value=DEFAULT_FINAL_SIZE,
            step=FINAL_SIZE_STEP,
        )
        dpi = st.selectbox(
            "DPI",
            options=list(ALLOWED_DPI_VALUES),
            index=list(ALLOWED_DPI_VALUES).index(DEFAULT_DPI),
            format_func=lambda value: DPI_LABELS.get(value, str(value)),
        )
        physical_size_mm = st.slider(
            "實體尺寸（mm）",
            min_value=20.0,
            max_value=100.0,
            value=DEFAULT_PHYSICAL_SIZE_MM,
            step=1.0,
        )
        module_block_size = st.slider("Module Block Size (m)", 7, 29, DEFAULT_MODULE_BLOCK_SIZE)
        centroid_size = st.slider("Centroid Size (ω)", 3, 15, DEFAULT_CENTROID_SIZE)
    else:
        assert selected is not None
        st.info(
            f"**{selected.label}** · {selected.final_size}px · {selected.dpi} DPI · "
            f"約 {selected.physical_size_mm:.0f}×{selected.physical_size_mm:.0f} mm"
        )
        if selected.module_block_size is not None:
            st.caption(f"m={selected.module_block_size} · ω={selected.centroid_size}")
        else:
            st.caption("m / ω 依網址長度與輸出尺寸自動計算")
        final_size = selected.final_size
        dpi = selected.dpi
        physical_size_mm = selected.physical_size_mm
        module_block_size = selected.module_block_size
        centroid_size = selected.centroid_size

    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("📖 操作手冊摘要", expanded=False):
        st.markdown(
            """
- **遠掃**讀網址 A · **近掃**讀網址 B（同一張 `fused_qr.png`）
- **m**：每模組像素邊長（建議 11 或依輸出自動）
- **ω**：中心質心邊長，建議 ≈ m/3
- 完整說明見 `docs/DUAL_INFO_MANUAL.md`
            """
        )

    st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
    generate = st.button(
        "開始融合生成 QR Code",
        type="primary",
        use_container_width=True,
    )
    return url_a, url_b, output_preset, module_block_size, centroid_size, final_size, dpi, physical_size_mm, generate


def render_application() -> None:
    """Render the full application after successful authentication."""
    st.markdown(
        """
<div class="hero-wrap">
  <p class="hero-title">Dual-Layer Smart QR Fusion Engine</p>
  <p class="hero-sub">
    雙資訊 QR（DUAL_INFO）· 遠距離讀取網址 A · 近距離讀取網址 B · 內建 AI 解碼驗證
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown('<p class="sidebar-heading">⚙️ 控制面板</p>', unsafe_allow_html=True)
        url_a, url_b, output_preset, module_block_size, centroid_size, final_size, dpi, physical_size_mm, generate = (
            render_sidebar_controls()
        )

    if generate:
        if not url_a.strip() or not url_b.strip():
            st.error("請填寫網址 A 與網址 B。")
        else:
            config = build_config_from_ui(
                url_a=url_a,
                url_b=url_b,
                output_preset=output_preset,
                module_block_size=module_block_size,
                centroid_size=centroid_size,
                final_size=final_size,
                dpi=dpi,
                physical_size_mm=physical_size_mm,
            )
            with st.spinner("正在融合矩陣、模擬掃描、驗證與 AI 解碼分析…"):
                try:
                    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                    run_pipeline(config)
                    st.session_state["last_run_ok"] = True
                    st.session_state["last_run_params"] = {
                        "final_size": final_size,
                        "dpi": dpi,
                        "output_preset": output_preset,
                        "url_a": url_a.strip(),
                        "url_b": url_b.strip(),
                    }
                    st.session_state["auto_decode"] = True
                    st.session_state["decode_results"] = run_decode_test(
                        expected_a=url_a.strip(),
                        expected_b=url_b.strip(),
                    )
                except Exception as exc:
                    st.session_state["last_run_ok"] = False
                    st.error(f"生成失敗：{exc}")
                    logging.exception("UI pipeline failed")

    if st.session_state.get("last_run_ok") or FUSED_IMAGE.exists():
        render_results()
    else:
        st.markdown(
            """
<div class="card">
  <p style="margin:0;color:var(--text-muted);">
    請在左側設定參數，點擊 <strong style="color:var(--accent);">開始融合生成 QR Code</strong>。
    生成後將自動執行 AI 解碼測試。
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Render the Streamlit application."""
    st.set_page_config(
        page_title="Dual-Layer QR Fusion Engine",
        page_icon="🔲",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    configure_logging(verbose=False)
    logging.getLogger().setLevel(logging.WARNING)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not st.session_state.get(SESSION_AUTH_KEY):
        render_auth_gate()
        return

    inject_custom_css()
    if st.session_state.pop("auth_welcome", False):
        st.success("驗證成功！核心防偽引擎已解鎖，完整測試介面已就緒。")
    render_application()


if __name__ == "__main__":
    main()
