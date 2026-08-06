"""QR matrix generation for marketing (A) and verification (B) layers."""

from __future__ import annotations

import logging
from typing import List

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

from config import ErrorCorrectionLevel, QRGeneratorConfig

logger = logging.getLogger(__name__)

QRMatrix = List[List[bool]]

_ERROR_CORRECTION_MAP = {
    ErrorCorrectionLevel.L: ERROR_CORRECT_L,
    ErrorCorrectionLevel.M: ERROR_CORRECT_M,
    ErrorCorrectionLevel.Q: ERROR_CORRECT_Q,
    ErrorCorrectionLevel.H: ERROR_CORRECT_H,
}


class QRMatrixGenerator:
    """Generate standard QR code binary matrices from payload strings."""

    def __init__(self, config: QRGeneratorConfig | None = None) -> None:
        """Initialize the generator with optional configuration."""
        self._config = config or QRGeneratorConfig()

    @property
    def config(self) -> QRGeneratorConfig:
        """Return the active generator configuration."""
        return self._config

    def generate(self, payload: str) -> QRMatrix:
        """Build a QR matrix for the given payload.

        Args:
            payload: Data encoded into the QR code.

        Returns:
            Binary matrix where True represents a dark module.
        """
        logger.info(
            "Generating QR matrix (ec=%s, version=%s)",
            self._config.error_correction.value,
            self._config.version,
        )
        qr = qrcode.QRCode(
            version=self._config.version,
            error_correction=_ERROR_CORRECTION_MAP[self._config.error_correction],
            box_size=1,
            border=self._config.border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        logger.debug("Generated matrix size: %dx%d", len(matrix), len(matrix[0]))
        return matrix

    @staticmethod
    def matrix_size(matrix: QRMatrix) -> int:
        """Return the square dimension of a QR matrix."""
        return len(matrix)


class QRVersionResolver:
    """Resolve a shared QR version so layer A/B matrices stay module-aligned."""

    @staticmethod
    def infer_version(payload: str, config: QRGeneratorConfig) -> int:
        """Infer the minimum QR version required for a payload."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=_ERROR_CORRECTION_MAP[config.error_correction],
            box_size=1,
            border=config.border,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        return qr.version

    @classmethod
    def resolve_shared_version(
        cls,
        url_a: str,
        url_b: str,
        config_a: QRGeneratorConfig,
        config_b: QRGeneratorConfig,
    ) -> int:
        """Return the larger version required by either payload."""
        version_a = cls.infer_version(url_a, config_a)
        version_b = cls.infer_version(url_b, config_b)
        shared = max(version_a, version_b)
        logger.info("Resolved shared QR version=%d (A=%d, B=%d)", shared, version_a, version_b)
        return shared


def sync_shared_qr_version(config_a: QRGeneratorConfig, config_b: QRGeneratorConfig, url_a: str, url_b: str) -> int:
    """Apply a shared QR version to both layer configs."""
    shared_version = QRVersionResolver.resolve_shared_version(url_a, url_b, config_a, config_b)
    config_a.version = shared_version
    config_b.version = shared_version
    return shared_version


class QRLayerGenerator:
    """Convenience wrapper for producing QR-A and QR-B matrices."""

    def __init__(
        self,
        qr_a_config: QRGeneratorConfig | None = None,
        qr_b_config: QRGeneratorConfig | None = None,
    ) -> None:
        """Initialize layer generators for A and B."""
        self._generator_a = QRMatrixGenerator(qr_a_config)
        self._generator_b = QRMatrixGenerator(qr_b_config)

    def generate_layer_a(self, url_a: str) -> QRMatrix:
        """Generate the marketing-layer QR matrix."""
        return self._generator_a.generate(url_a)

    def generate_layer_b(self, url_b: str) -> QRMatrix:
        """Generate the verification-layer QR matrix."""
        return self._generator_b.generate(url_b)
