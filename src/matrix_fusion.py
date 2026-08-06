"""Matrix-level dual-information QR fusion (Zhou & Wang, Sensors 2024)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from config import (
    FINDER_PATTERN_SIZE,
    FINDER_SEPARATOR_BORDER,
    FusionConfig,
    MIN_QR_VERSION_SIZE,
    TIMING_PATTERN_COL,
    TIMING_PATTERN_ROW,
    VERSION_INFO_THRESHOLD,
)
from dual_info_qr import fuse_dual_info_matrices, resolve_dual_info_sizes

logger = logging.getLogger(__name__)

GrayscaleMatrix = np.ndarray


@dataclass(frozen=True)
class FusionResult:
    """Output of matrix fusion including sub-module expansion metadata."""

    matrix: GrayscaleMatrix
    qr_module_size: int
    sub_module_factor: int


class QRStructureMask:
    """Identify QR function-pattern modules (used by validation helpers)."""

    @staticmethod
    def infer_version(matrix_size: int) -> int:
        """Infer QR version number from matrix edge length."""
        if matrix_size < MIN_QR_VERSION_SIZE:
            return 1
        return (matrix_size - MIN_QR_VERSION_SIZE) // 4 + 1

    @classmethod
    def build(cls, matrix_size: int) -> np.ndarray:
        """Build a mask where True marks protected function-pattern modules."""
        if matrix_size < MIN_QR_VERSION_SIZE:
            return np.ones((matrix_size, matrix_size), dtype=bool)

        function_mask = np.zeros((matrix_size, matrix_size), dtype=bool)

        def mark_rect(row: int, col: int, height: int, width: int) -> None:
            row_end = min(matrix_size, row + height)
            col_end = min(matrix_size, col + width)
            function_mask[row:row_end, col:col_end] = True

        mark_rect(0, 0, FINDER_SEPARATOR_BORDER, FINDER_SEPARATOR_BORDER)
        mark_rect(0, matrix_size - FINDER_PATTERN_SIZE - 1, FINDER_PATTERN_SIZE + 1, FINDER_PATTERN_SIZE + 1)
        mark_rect(matrix_size - FINDER_PATTERN_SIZE - 1, 0, FINDER_PATTERN_SIZE + 1, FINDER_PATTERN_SIZE + 1)

        function_mask[TIMING_PATTERN_ROW, FINDER_SEPARATOR_BORDER : matrix_size - FINDER_SEPARATOR_BORDER] = True
        function_mask[FINDER_SEPARATOR_BORDER : matrix_size - FINDER_SEPARATOR_BORDER, TIMING_PATTERN_COL] = True
        function_mask[FINDER_SEPARATOR_BORDER - 1, 0:FINDER_SEPARATOR_BORDER] = True
        function_mask[0:FINDER_SEPARATOR_BORDER, FINDER_SEPARATOR_BORDER - 1] = True
        function_mask[FINDER_SEPARATOR_BORDER - 1, matrix_size - FINDER_SEPARATOR_BORDER : matrix_size] = True
        function_mask[0:FINDER_SEPARATOR_BORDER, matrix_size - FINDER_SEPARATOR_BORDER] = True
        function_mask[matrix_size - FINDER_SEPARATOR_BORDER, 0:FINDER_SEPARATOR_BORDER] = True
        function_mask[matrix_size - FINDER_SEPARATOR_BORDER : matrix_size, FINDER_SEPARATOR_BORDER - 1] = True

        version = cls.infer_version(matrix_size)
        if version >= VERSION_INFO_THRESHOLD:
            mark_rect(0, matrix_size - 11, 6, 3)
            mark_rect(matrix_size - 11, 0, 3, 6)

        return function_mask


class MatrixFusionEngine:
    """Fuse two QR binary matrices into a dual-information grayscale matrix."""

    def __init__(self, config: FusionConfig | None = None, *, final_size: int | None = None) -> None:
        """Initialize the fusion engine."""
        self._config = config or FusionConfig()
        self._final_size = final_size

    @property
    def config(self) -> FusionConfig:
        """Return active fusion configuration."""
        return self._config

    @staticmethod
    def align_matrices(matrix_a: List[List[bool]], matrix_b: List[List[bool]]) -> tuple[np.ndarray, np.ndarray]:
        """Pad matrices to a common square size with white (False) modules."""
        size = max(len(matrix_a), len(matrix_b))
        aligned_a = np.zeros((size, size), dtype=bool)
        aligned_b = np.zeros((size, size), dtype=bool)

        offset_a = (size - len(matrix_a)) // 2
        offset_b = (size - len(matrix_b)) // 2

        for row_idx, row in enumerate(matrix_a):
            aligned_a[offset_a + row_idx, offset_a : offset_a + len(row)] = row
        for row_idx, row in enumerate(matrix_b):
            aligned_b[offset_b + row_idx, offset_b : offset_b + len(row)] = row

        return aligned_a, aligned_b

    def fuse(self, matrix_far: List[List[bool]], matrix_near: List[List[bool]]) -> FusionResult:
        """Fuse QR-A (far) and QR-B (near) using near-far dual-state modules."""
        logger.info("Fusing matrices using dual-information mode (far=A, near=B)")
        aligned_far, aligned_near = self.align_matrices(matrix_far, matrix_near)
        height = aligned_far.shape[0]
        m, omega = resolve_dual_info_sizes(
            height,
            self._final_size or 1200,
            self._config.module_block_size,
            self._config.centroid_size,
        )
        fused = fuse_dual_info_matrices(
            aligned_far,
            aligned_near,
            module_block_size=m,
            centroid_size=omega,
        )
        return FusionResult(matrix=fused, qr_module_size=height, sub_module_factor=m)
