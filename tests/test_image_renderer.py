"""Unit tests for image renderer."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from config import RenderConfig
from image_renderer import ImageRenderEngine


def test_quiet_zone_expands_matrix(tmp_path: Path) -> None:
    """Quiet zone padding should increase matrix dimensions."""
    renderer = ImageRenderEngine(RenderConfig(quiet_zone_modules=2))
    base = np.zeros((4, 4), dtype=np.uint8)
    padded = renderer.add_quiet_zone(base)
    assert padded.shape == (8, 8)
    assert padded[0, 0] == 255


def test_render_png_writes_file(tmp_path: Path) -> None:
    """Renderer should create a PNG file on disk."""
    renderer = ImageRenderEngine(RenderConfig(module_scale=4, dpi=300))
    matrix = np.full((5, 5), 128, dtype=np.uint8)
    output = renderer.render_png(matrix, tmp_path / "test.png", module_scale=4)
    assert output.exists()
    assert output.stat().st_size > 0
