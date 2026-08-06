"""Long URL payload regression tests (approx. 36–180 bit payloads)."""

from __future__ import annotations

import json
from pathlib import Path

from config import AppConfig, apply_output_preset
from run_poc import run_pipeline


def _run_and_assert(url_a: str, url_b: str, output_dir: str, preset: str = "hi_res") -> dict:
    config = AppConfig()
    config.url_a = url_a
    config.url_b = url_b
    config.output_dir = output_dir
    apply_output_preset(config, preset)

    run_pipeline(config)

    report = json.loads(Path(output_dir, "validation_report.json").read_text(encoding="utf-8"))
    assert report["output_pixel_width"] == report["output_pixel_height"] == config.render.final_size
    assert report["fusion_mode"] == "dual_info"
    return report


def test_short_urls_near_and_far_decode() -> None:
    """Short URLs (~36 bit class) should pass both layers."""
    report = _run_and_assert(
        "https://a.example/1",
        "https://b.example/2",
        "output/test_short_urls",
        preset="screen",
    )
    assert report["qr_a_detected"] is True
    assert report["qr_b_detected"] is True


def test_medium_urls_near_and_far_decode() -> None:
    """Medium government-style URLs should pass both layers."""
    report = _run_and_assert(
        "https://www.ppmof.gov.tw/",
        "https://www.pptms.net/PMP/#government",
        "output/test_medium_urls",
    )
    assert report["qr_a_detected"] is True
    assert report["qr_b_detected"] is True


def test_long_urls_near_and_far_decode() -> None:
    """Long URLs (~180 bit class) should still pass with adaptive EC/fusion tuning."""
    long_a = (
        "https://verify.example.com/marketing/campaign/2026/spring/"
        "promo?utm_source=print&utm_medium=qr&utm_campaign=dual-layer-test"
    )
    long_b = (
        "https://secure.example.com/token/verify/"
        "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
    )
    report = _run_and_assert(long_a, long_b, "output/test_long_urls", preset="large")
    assert report["qr_a_detected"] is True
    assert report["qr_b_detected"] is True
    assert report["qr_version"] is not None
    assert report["qr_version"] >= 4
