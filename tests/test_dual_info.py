"""Tests for Zhou & Wang dual-information QR fusion (Sensors 2024)."""

from __future__ import annotations

import numpy as np

from config import AppConfig, FusionConfig, apply_output_preset
from dual_info_qr import (
    build_dual_state_module,
    fuse_dual_info_matrices,
    recover_far_matrix_from_dual,
    recover_near_matrix_from_dual,
)
from matrix_fusion import MatrixFusionEngine
from qr_generator import QRLayerGenerator
from run_poc import run_pipeline
from validator import FusionValidator


def test_dual_state_module_shapes() -> None:
    """Each dual-state module should be m×m with distinct center/outer colors."""
    cell = build_dual_state_module(near_dark=True, far_dark=False, module_size=11, centroid_size=3)
    assert cell.shape == (11, 11)
    assert cell[0, 0] != cell[5, 5]


def test_fuse_and_recover_roundtrip() -> None:
    """Fused matrix should recover both near and far bit patterns."""
    matrix_far = np.array(
        [
            [True, False],
            [False, True],
        ],
        dtype=bool,
    )
    matrix_near = np.array(
        [
            [False, True],
            [True, False],
        ],
        dtype=bool,
    )
    m, omega = 11, 3
    fused = fuse_dual_info_matrices(matrix_far, matrix_near, module_block_size=m, centroid_size=omega)
    recovered_far = recover_far_matrix_from_dual(fused, 2, m)
    recovered_near = recover_near_matrix_from_dual(fused, 2, m, omega)
    np.testing.assert_array_equal(recovered_far, matrix_far)
    np.testing.assert_array_equal(recovered_near, matrix_near)


def test_dual_info_pipeline_decodes_both_urls() -> None:
    """Full pipeline should decode URL A (far) and URL B (near)."""
    config = AppConfig()
    config.url_a = "https://example.com/far-layer"
    config.url_b = "https://example.com/near-layer"
    config.output_dir = "output/test_dual_info"
    apply_output_preset(config, "screen")

    run_pipeline(config)

    layer_gen = QRLayerGenerator(config.qr_a, config.qr_b)
    matrix_a = np.array(layer_gen.generate_layer_a(config.url_a), dtype=bool)
    matrix_b = np.array(layer_gen.generate_layer_b(config.url_b), dtype=bool)
    engine = MatrixFusionEngine(config.fusion, final_size=config.render.final_size)
    result = engine.fuse(matrix_a.tolist(), matrix_b.tolist())

    validator = FusionValidator(
        expected_url_a=config.url_a,
        expected_url_b=config.url_b,
        sub_module_factor=result.sub_module_factor,
        fusion_centroid_size=config.fusion.centroid_size,
    )
    decoded_a, decoded_b, _, _ = validator._decode_dual_info_matrices(result.matrix, result.qr_module_size)
    assert config.url_a in decoded_a
    assert config.url_b in decoded_b


def test_matrix_fusion_engine_dual_info_mode() -> None:
    """MatrixFusionEngine should produce expanded sub-module matrix."""
    engine = MatrixFusionEngine(
        FusionConfig(module_block_size=7, centroid_size=3, auto_tune=False),
        final_size=1200,
    )
    matrix = [[True, False], [False, True]]
    result = engine.fuse(matrix, matrix)
    assert result.sub_module_factor == 7
    assert result.matrix.shape == (14, 14)
