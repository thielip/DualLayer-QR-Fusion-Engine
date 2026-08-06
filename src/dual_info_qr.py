"""Dual-information QR fusion per Zhou & Wang, Sensors 2024, 24(10), 3055.

Each module block (m×m px) encodes:
  - center ω×ω region → near-range message (QR-B)
  - outer ring        → far-range message (QR-A)
"""

from __future__ import annotations

import logging

import numpy as np

from config import MAX_GRAY_VALUE, MIN_GRAY_VALUE

logger = logging.getLogger(__name__)


def resolve_dual_info_sizes(
    qr_module_size: int,
    final_size: int,
    module_block_size: int | None = None,
    centroid_size: int | None = None,
) -> tuple[int, int]:
    """Pick module block size m and centroid ω (paper: ω ≈ m/3)."""
    quiet = 4
    modules_total = qr_module_size + quiet * 2
    px_per_module = max(7, final_size // max(1, modules_total))

    if module_block_size is None:
        module_block_size = max(7, min(29, px_per_module))
    m = max(7, min(29, module_block_size))

    if centroid_size is None:
        centroid_size = max(3, m // 3)
    omega = max(3, min(m - 2, centroid_size))
    if omega >= m:
        omega = max(3, m // 3)

    logger.info("Dual-info params: m=%d omega=%d (qr_modules=%d)", m, omega, qr_module_size)
    return m, omega


def build_dual_state_module(near_dark: bool, far_dark: bool, module_size: int, centroid_size: int) -> np.ndarray:
    """Build one m×m dual-state module (Table 1 in the paper)."""
    far_value = MIN_GRAY_VALUE if far_dark else MAX_GRAY_VALUE
    near_value = MIN_GRAY_VALUE if near_dark else MAX_GRAY_VALUE
    cell = np.full((module_size, module_size), far_value, dtype=np.uint8)
    offset = (module_size - centroid_size) // 2
    end = offset + centroid_size
    cell[offset:end, offset:end] = near_value
    return cell


def fuse_dual_info_matrices(
    matrix_far: np.ndarray,
    matrix_near: np.ndarray,
    *,
    module_block_size: int,
    centroid_size: int,
    function_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Fuse aligned far/near QR boolean matrices into a sub-module grayscale matrix."""
    height, width = matrix_far.shape
    m = module_block_size
    omega = centroid_size
    fused = np.zeros((height * m, width * m), dtype=np.uint8)

    for row in range(height):
        for col in range(width):
            far_dark = bool(matrix_far[row, col])
            near_dark = bool(matrix_near[row, col])
            if function_mask is not None and function_mask[row, col]:
                value = MIN_GRAY_VALUE if far_dark else MAX_GRAY_VALUE
                cell = np.full((m, m), value, dtype=np.uint8)
            else:
                cell = build_dual_state_module(near_dark, far_dark, m, omega)
            fused[row * m : (row + 1) * m, col * m : (col + 1) * m] = cell

    return fused


def recover_near_matrix_from_dual(
    fused: np.ndarray,
    qr_module_size: int,
    module_block_size: int,
    centroid_size: int,
    threshold: int = 128,
) -> np.ndarray:
    """Recover near QR modules by sampling each block's centroid region."""
    recovered = np.zeros((qr_module_size, qr_module_size), dtype=bool)
    offset = (module_block_size - centroid_size) // 2
    end = offset + centroid_size
    for row in range(qr_module_size):
        for col in range(qr_module_size):
            block = fused[
                row * module_block_size : (row + 1) * module_block_size,
                col * module_block_size : (col + 1) * module_block_size,
            ]
            center = block[offset:end, offset:end]
            recovered[row, col] = float(np.mean(center)) < threshold
    return recovered


def recover_far_matrix_from_dual(
    fused: np.ndarray,
    qr_module_size: int,
    module_block_size: int,
    threshold: int = 128,
) -> np.ndarray:
    """Recover far QR modules by averaging the full module block."""
    recovered = np.zeros((qr_module_size, qr_module_size), dtype=bool)
    for row in range(qr_module_size):
        for col in range(qr_module_size):
            block = fused[
                row * module_block_size : (row + 1) * module_block_size,
                col * module_block_size : (col + 1) * module_block_size,
            ]
            recovered[row, col] = float(np.mean(block)) < threshold
    return recovered
