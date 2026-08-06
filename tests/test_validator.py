"""Unit tests for validation pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from config import FusionConfig, RenderConfig, SimulationConfig, VALIDATION_REPORT_FILENAME
from image_renderer import ImageRenderEngine
from matrix_fusion import MatrixFusionEngine
from qr_generator import QRLayerGenerator
from validator import FusionValidator, ValidationReport


def test_validation_report_serializes_to_json() -> None:
    """Validation report should serialize to the expected schema."""
    report = ValidationReport(
        qr_a_detected=True,
        qr_b_detected=False,
        blur_level=3,
        dpi=300,
        final_size=1200,
        distance_profile="far",
    )
    payload = report.to_dict()
    assert payload["qr_a_detected"] is True
    assert payload["distance_profile"] == "far"
    assert payload["fusion_mode"] == "dual_info"


def test_validator_writes_report_file(tmp_path: Path) -> None:
    """Validator should emit validation_report.json."""
    layers = QRLayerGenerator()
    matrix_a = layers.generate_layer_a("https://example.com/a")
    matrix_b = layers.generate_layer_b("https://example.com/b")

    fused = MatrixFusionEngine(FusionConfig(), final_size=1200).fuse(matrix_a, matrix_b)
    renderer = ImageRenderEngine(RenderConfig(module_scale=6, dpi=300, physical_size_mm=0, final_size=1200))
    pixel = renderer.build_pixel_image(
        fused.matrix,
        qr_module_size=fused.qr_module_size,
        sub_module_factor=fused.sub_module_factor,
        final_size=1200,
    )

    validator = FusionValidator(
        expected_url_a="https://example.com/a",
        expected_url_b="https://example.com/b",
        simulation_config=SimulationConfig(blur_level=1),
        render_config=RenderConfig(dpi=300, final_size=1200),
        sub_module_factor=fused.sub_module_factor,
        fusion_centroid_size=3,
    )
    report = validator.validate_fused_image(
        pixel,
        tmp_path,
        fusion_matrix=fused.matrix,
        qr_module_size=fused.qr_module_size,
    )
    report_path = tmp_path / VALIDATION_REPORT_FILENAME
    assert report_path.exists()
    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert "qr_a_detected" in loaded
    assert "qr_b_detected" in loaded
    assert isinstance(report.qr_a_detected, bool)
