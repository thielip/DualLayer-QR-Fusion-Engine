"""UI decode regression tests using competition demo URLs."""

from __future__ import annotations

from pathlib import Path

from config import AppConfig, apply_output_preset
from run_poc import run_pipeline


def test_ui_decode_user_screenshot_urls() -> None:
    """Far/near output images should decode with the screenshot test URLs."""
    from app_main import run_decode_test

    config = AppConfig()
    config.url_a = "https://www.ppmof.gov.tw/"
    config.url_b = "https://www.ppmof.net/PMP/#government-trust"
    config.output_dir = "output/test_ui_decode"
    apply_output_preset(config, "a4_print")

    run_pipeline(config)

    results = run_decode_test(
        expected_a=config.url_a,
        expected_b=config.url_b,
        output_dir=Path(config.output_dir),
    )
    assert results["fused_far"].success is True
    assert results["fused_near"].success is True
    assert results["far_direct"].success is True
    assert config.url_a in (results["fused_far"].matched or "")
    assert config.url_b in (results["fused_near"].matched or "")
