"""Adaptive fusion parameters for variable-length URL payloads."""

from __future__ import annotations

import logging

from config import AppConfig, ErrorCorrectionLevel

logger = logging.getLogger(__name__)


def qr_version_to_module_size(version: int) -> int:
    """Convert QR version number to module count per side."""
    return 21 + 4 * (version - 1)


def _apply_ec_level(config: AppConfig) -> None:
    """Dual-info QR works best with matching low EC on both layers."""
    config.qr_a.error_correction = ErrorCorrectionLevel.L
    config.qr_b.error_correction = ErrorCorrectionLevel.L


def _apply_dual_info_tuning(config: AppConfig, qr_module_size: int) -> None:
    """Auto-compute module block size m and centroid ω when enabled."""
    if not config.fusion.auto_tune:
        return

    pixels_per_module = config.render.final_size / max(1, qr_module_size + config.render.quiet_zone_modules * 2)
    m = max(7, min(29, int(pixels_per_module * 0.9)))
    if qr_module_size <= 25:
        m = max(m, 11)
    config.fusion.module_block_size = m
    config.fusion.centroid_size = max(3, m // 3)


def prepare_config_for_payloads(config: AppConfig, url_a: str, url_b: str) -> int:
    """Adapt EC/fusion settings and sync shared QR version for URL length."""
    from qr_generator import sync_shared_qr_version

    _apply_ec_level(config)
    sync_shared_qr_version(config.qr_a, config.qr_b, url_a, url_b)
    module_size = qr_version_to_module_size(config.qr_a.version or 1)
    _apply_dual_info_tuning(config, module_size)
    logger.info(
        "Prepared payloads: preset=%s version=%s modules=%d ec=%s m=%s omega=%s auto_tune=%s",
        config.output_preset,
        config.qr_a.version,
        module_size,
        config.qr_a.error_correction.value,
        config.fusion.module_block_size,
        config.fusion.centroid_size,
        config.fusion.auto_tune,
    )
    return module_size
