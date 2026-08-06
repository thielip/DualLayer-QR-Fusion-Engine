"""Unit tests for QR matrix generation."""

from __future__ import annotations

from config import ErrorCorrectionLevel, QRGeneratorConfig
from qr_generator import QRLayerGenerator, QRMatrixGenerator


def test_generate_matrix_returns_square_bool_grid() -> None:
    """QR generator should return a non-empty square matrix."""
    generator = QRMatrixGenerator()
    matrix = generator.generate("https://example.com/test")
    assert len(matrix) == len(matrix[0])
    assert all(isinstance(cell, bool) for row in matrix for cell in row)


def test_error_correction_levels_are_supported() -> None:
    """All configured EC levels should produce valid matrices."""
    for level in ErrorCorrectionLevel:
        generator = QRMatrixGenerator(QRGeneratorConfig(error_correction=level))
        matrix = generator.generate("payload")
        assert QRMatrixGenerator.matrix_size(matrix) > 0


def test_layer_generator_produces_two_matrices() -> None:
    """Layer generator should produce independent A/B matrices."""
    layers = QRLayerGenerator()
    matrix_a = layers.generate_layer_a("https://a.example")
    matrix_b = layers.generate_layer_b("https://b.example")
    assert matrix_a
    assert matrix_b
