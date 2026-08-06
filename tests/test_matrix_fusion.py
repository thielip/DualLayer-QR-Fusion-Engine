"""Unit tests for dual-information matrix fusion engine."""

from __future__ import annotations

import numpy as np

from config import FusionConfig
from matrix_fusion import MatrixFusionEngine, QRStructureMask


def _sample_matrix(size: int, fill: bool) -> list[list[bool]]:
    return [[fill for _ in range(size)] for _ in range(size)]


def test_fuse_aligns_different_sizes() -> None:
    """Fusion should pad mismatched matrices to a common QR module size."""
    engine = MatrixFusionEngine(FusionConfig(), final_size=1200)
    result = engine.fuse(_sample_matrix(3, True), _sample_matrix(5, False))
    assert result.qr_module_size == 5
    assert result.sub_module_factor >= 7


def test_fused_matrix_values_are_uint8() -> None:
    """Fused output should be a grayscale uint8 matrix."""
    engine = MatrixFusionEngine(FusionConfig(module_block_size=11, centroid_size=3), final_size=1200)
    matrix_a = [
        [True, False],
        [False, True],
    ]
    matrix_b = [
        [False, True],
        [True, False],
    ]
    result = engine.fuse(matrix_a, matrix_b)
    assert result.matrix.dtype == np.uint8
    assert result.matrix.min() >= 0
    assert result.matrix.max() <= 255
    assert result.matrix.shape == (22, 22)


def test_structure_mask_protects_finder_region() -> None:
    """Function mask should mark finder corner modules as protected."""
    mask = QRStructureMask.build(29)
    assert mask[0, 0]
    assert mask[6, 6]
    assert not mask[15, 15]


def test_dual_info_expands_sub_module_cells() -> None:
    """Each QR module should expand to an m×m pixel block."""
    engine = MatrixFusionEngine(
        FusionConfig(module_block_size=7, centroid_size=3),
        final_size=1200,
    )
    result = engine.fuse(_sample_matrix(21, False), _sample_matrix(21, False))
    assert result.sub_module_factor == 7
    assert result.matrix.shape == (147, 147)
