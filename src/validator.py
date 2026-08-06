"""Validation pipeline for dual-information QR fusion."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import zxingcpp
from PIL import Image

from config import (
    FUSION_MODE,
    DistanceProfile,
    FAR_BINARIZE_THRESHOLD,
    MAX_GRAY_VALUE,
    MIN_GRAY_VALUE,
    NEAR_BINARIZE_THRESHOLD,
    RenderConfig,
    SimulationConfig,
    VALIDATION_REPORT_FILENAME,
)
from dual_info_qr import recover_far_matrix_from_dual, recover_near_matrix_from_dual
from image_renderer import ImageRenderEngine
from imgops import gaussian_blur, threshold_binary, threshold_otsu
from simulation import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Structured validation output."""

    qr_a_detected: bool
    qr_b_detected: bool
    blur_level: int
    dpi: int
    final_size: int
    distance_profile: str
    fusion_mode: str = FUSION_MODE
    output_preset: str = "a4_print"
    qr_a_direct_scan: bool = False
    qr_b_near_scan: bool = False
    output_pixel_width: int = 0
    output_pixel_height: int = 0
    qr_version: int | None = None
    module_block_size: int | None = None
    centroid_size: int | None = None
    decoded_qr_a: str | None = None
    decoded_qr_b: str | None = None
    notes: str = (
        "PoC validation only; detection rates depend on device, optics, and print quality."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert report to a JSON-serializable dictionary."""
        return asdict(self)


class QRDecoder:
    """Decode QR payloads from grayscale or RGB images using zxing-cpp."""

    def decode_multi(self, image: np.ndarray) -> list[str]:
        """Decode all QR codes detected in an image."""
        try:
            barcodes = zxingcpp.read_barcodes(image)
        except Exception:
            try:
                pil = Image.fromarray(image)
                barcodes = zxingcpp.read_barcodes(pil)
            except Exception:
                logger.exception("zxing-cpp decode failed")
                return []
        payloads: list[str] = []
        for item in barcodes:
            text = (item.text or "").strip()
            if text:
                payloads.append(text)
        return payloads

    def _preprocess_variants(
        self,
        image: np.ndarray,
        profile: DistanceProfile | None = None,
    ) -> list[np.ndarray]:
        """Generate binarized / blurred views suited for near or far decode attempts."""
        variants: list[np.ndarray] = [image]
        working = image if image.ndim == 2 else image[:, :, 0]

        if profile == DistanceProfile.FAR:
            # Optical far scan averages modules → blur washes out the near centroid (ω).
            for kernel in (5, 7, 9, 11):
                variants.append(gaussian_blur(working, kernel, sigma=kernel / 3.0))
            thresholds = [FAR_BINARIZE_THRESHOLD, 180, 160, 128]
        elif profile == DistanceProfile.NEAR:
            thresholds = [NEAR_BINARIZE_THRESHOLD, 72, 96, 120]
        else:
            thresholds = [128]

        for threshold in thresholds:
            variants.append(threshold_binary(working, threshold))
            if profile == DistanceProfile.FAR:
                blurred = gaussian_blur(working, 7, sigma=2.5)
                variants.append(threshold_binary(blurred, threshold))

        variants.append(threshold_otsu(working))
        return variants

    def decode_with_retries(
        self,
        image: np.ndarray,
        profile: DistanceProfile | None = None,
    ) -> list[str]:
        """Try multiple preprocess variants and aggregate unique decoded payloads."""
        decoded: list[str] = []
        seen: set[str] = set()
        for variant in self._preprocess_variants(image, profile):
            for payload in self.decode_multi(variant):
                if payload not in seen:
                    seen.add(payload)
                    decoded.append(payload)
        return decoded


class LayerRecoveryEngine:
    """Upscale recovered QR module matrices for barcode decoding."""

    def matrix_to_decode_image(self, matrix: np.ndarray, module_scale: int = 12) -> np.ndarray:
        """Upscale a binary QR matrix for detector-friendly decoding."""
        quiet = np.full((4, matrix.shape[1]), MAX_GRAY_VALUE, dtype=np.uint8)
        bordered = np.vstack([quiet, matrix, quiet])
        quiet_rows = np.full((bordered.shape[0], 4), MAX_GRAY_VALUE, dtype=np.uint8)
        bordered = np.hstack([quiet_rows, bordered, quiet_rows])
        return np.repeat(np.repeat(bordered, module_scale, axis=0), module_scale, axis=1)


class FusionValidator:
    """Validate whether QR-A and QR-B remain decodable under simulated scans."""

    def __init__(
        self,
        expected_url_a: str,
        expected_url_b: str,
        simulation_config: SimulationConfig | None = None,
        render_config: RenderConfig | None = None,
        sub_module_factor: int = 1,
        fusion_centroid_size: int | None = None,
        qr_version: int | None = None,
        output_preset: str = "a4_print",
    ) -> None:
        """Initialize validator with expected payloads."""
        self._expected_url_a = expected_url_a
        self._expected_url_b = expected_url_b
        self._sub_module_factor = sub_module_factor
        self._fusion_centroid_size = fusion_centroid_size
        self._qr_version = qr_version
        self._output_preset = output_preset
        self._simulation = SimulationEngine(simulation_config)
        self._renderer = ImageRenderEngine(render_config)
        self._decoder = QRDecoder()
        self._recovery = LayerRecoveryEngine()

    def _match_payload(self, decoded_values: list[str], expected: str) -> tuple[bool, str | None]:
        """Check whether expected payload appears among decoded values."""
        for value in decoded_values:
            if value == expected or expected in value or value in expected:
                return True, value
        return False, None

    def _match_payload_b(
        self,
        decoded_values: list[str],
        expected_b: str,
        expected_a: str,
    ) -> tuple[bool, str | None]:
        """Match QR-B while ignoring QR-A payloads."""
        for value in decoded_values:
            if value and (value == expected_a or expected_a in value or value in expected_a):
                continue
            if value == expected_b or expected_b in value or value in expected_b:
                return True, value
        return False, None

    def _decode_dual_info_matrices(
        self,
        fusion_matrix: np.ndarray,
        qr_module_size: int,
    ) -> tuple[list[str], list[str], np.ndarray, np.ndarray]:
        """Decode using Zhou & Wang dual-information module recovery."""
        m = self._sub_module_factor
        omega = self._fusion_centroid_size or max(3, m // 3)
        recovered_a_bool = recover_far_matrix_from_dual(fusion_matrix, qr_module_size, m)
        recovered_b_bool = recover_near_matrix_from_dual(fusion_matrix, qr_module_size, m, omega)
        recovered_a = recovered_a_bool.astype(np.uint8) * MIN_GRAY_VALUE + (~recovered_a_bool).astype(np.uint8) * MAX_GRAY_VALUE
        recovered_b = recovered_b_bool.astype(np.uint8) * MIN_GRAY_VALUE + (~recovered_b_bool).astype(np.uint8) * MAX_GRAY_VALUE
        image_a = self._recovery.matrix_to_decode_image(recovered_a)
        image_b = self._recovery.matrix_to_decode_image(recovered_b)
        return (
            self._decoder.decode_with_retries(image_a, DistanceProfile.FAR),
            self._decoder.decode_with_retries(image_b, DistanceProfile.NEAR),
            image_a,
            image_b,
        )

    def validate_fused_image(
        self,
        fused_image: np.ndarray,
        output_dir: str | Path,
        fusion_matrix: np.ndarray | None = None,
        qr_module_size: int | None = None,
        near_scan_image: np.ndarray | None = None,
        distance_profile: DistanceProfile = DistanceProfile.FAR,
    ) -> ValidationReport:
        """Run near/far simulations and attempt decoding on each."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        near_result = self._simulation.simulate_near(fused_image)
        far_result = self._simulation.simulate_far(fused_image)

        self._renderer.render_png(near_result.image, output_path / "validation_near.png")
        self._renderer.render_png(far_result.image, output_path / "validation_far.png")

        active_result = far_result if distance_profile == DistanceProfile.FAR else near_result

        decoded_a_candidates = self._decoder.decode_with_retries(far_result.image, DistanceProfile.FAR)
        decoded_a_candidates += self._decoder.decode_with_retries(fused_image, DistanceProfile.FAR)
        decoded_b_candidates: list[str] = []

        if near_scan_image is not None:
            decoded_b_candidates += self._decoder.decode_with_retries(near_scan_image, DistanceProfile.NEAR)

        recovered_a_img: np.ndarray | None = None
        recovered_b_img: np.ndarray | None = None
        if fusion_matrix is not None and qr_module_size is not None:
            recovered_a_far_matrix, recovered_b_near_matrix, recovered_a_img, recovered_b_img = (
                self._decode_dual_info_matrices(fusion_matrix, qr_module_size)
            )
            decoded_a_candidates.extend(recovered_a_far_matrix)
            decoded_b_candidates.extend(recovered_b_near_matrix)
            if recovered_a_img is not None:
                self._renderer.save_pixel_png(recovered_a_img, output_path / "recovered_layer_a.png")
            if recovered_b_img is not None:
                self._renderer.save_pixel_png(recovered_b_img, output_path / "recovered_layer_b.png")

        qr_a_direct, _ = self._match_payload(
            self._decoder.decode_with_retries(far_result.image, DistanceProfile.FAR),
            self._expected_url_a,
        )
        qr_b_near, _ = self._match_payload_b(
            decoded_b_candidates,
            self._expected_url_b,
            self._expected_url_a,
        )
        qr_a_detected, decoded_a = self._match_payload(decoded_a_candidates, self._expected_url_a)
        qr_b_detected, decoded_b = self._match_payload_b(
            decoded_b_candidates,
            self._expected_url_b,
            self._expected_url_a,
        )

        report = ValidationReport(
            qr_a_detected=qr_a_detected,
            qr_b_detected=qr_b_detected,
            qr_a_direct_scan=qr_a_direct,
            qr_b_near_scan=qr_b_near,
            blur_level=active_result.blur_level,
            dpi=self._renderer.config.dpi,
            final_size=self._renderer.config.final_size,
            distance_profile=distance_profile.value,
            output_preset=self._output_preset,
            output_pixel_width=int(fused_image.shape[1]),
            output_pixel_height=int(fused_image.shape[0]),
            qr_version=self._qr_version,
            module_block_size=self._sub_module_factor,
            centroid_size=self._fusion_centroid_size,
            decoded_qr_a=decoded_a,
            decoded_qr_b=decoded_b,
        )

        report_path = output_path / VALIDATION_REPORT_FILENAME
        report_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Validation report written: %s", report_path)
        return report
