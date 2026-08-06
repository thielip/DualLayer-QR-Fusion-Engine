"""Near/far decode regression tests with real-world style URLs."""

from __future__ import annotations

import json
from pathlib import Path

from config import AppConfig
from run_poc import run_pipeline


def test_user_urls_dual_info_near_and_far_decode() -> None:
    """Government URLs should decode A at far simulation and B at near paths."""
    config = AppConfig()
    config.url_a = "https://www.ppmof.gov.tw/"
    config.url_b = "https://www.pptms.net/PMP/#government"
    config.output_dir = "output/test_user_urls"
    config.output_preset = "a4_print"

    run_pipeline(config)

    report = json.loads(Path(config.output_dir, "validation_report.json").read_text(encoding="utf-8"))
    assert report["qr_a_detected"] is True
    assert report["qr_b_detected"] is True
    assert report["fusion_mode"] == "dual_info"
