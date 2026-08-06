"""Render fused QR matrices to physical PNG images."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image

from config import RenderConfig
from imgops import resize

logger = logging.getLogger(__name__)

MM_PER_INCH = 25.4


class ImageRenderEngine:
    """Convert module matrices into print-ready PNG images."""

    def __init__(self, config: RenderConfig | None = None) -> None:
        """Initialize renderer with optional configuration."""
        self._config = config or RenderConfig()

    @property
    def config(self) -> RenderConfig:
        """Return active render configuration."""
        return self._config

    def add_quiet_zone(self, matrix: np.ndarray, quiet_modules: int | None = None) -> np.ndarray:
        """Surround a module matrix with a white quiet zone."""
        border = quiet_modules if quiet_modules is not None else self._config.quiet_zone_modules
        if border <= 0:
            return matrix
        if matrix.ndim == 2:
            padded = np.full(
                (matrix.shape[0] + border * 2, matrix.shape[1] + border * 2),
                255,
                dtype=matrix.dtype,
            )
            padded[border : border + matrix.shape[0], border : border + matrix.shape[1]] = matrix
            return padded
        raise ValueError("Expected a 2D matrix for quiet zone padding.")

    def module_scale_for_physical_size(self, matrix: np.ndarray, physical_size_mm: float) -> int:
        """Compute module pixel scale to match target physical size."""
        modules_with_quiet = matrix.shape[0] + self._config.quiet_zone_modules * 2
        target_pixels = int(round(physical_size_mm / MM_PER_INCH * self._config.dpi))
        scale = max(1, target_pixels // modules_with_quiet)
        logger.debug(
            "Computed module scale=%d for %.1fmm at %d DPI",
            scale,
            physical_size_mm,
            self._config.dpi,
        )
        return scale

    def add_quiet_zone_for_fusion(
        self,
        matrix: np.ndarray,
        qr_module_size: int,
        sub_module_factor: int,
        quiet_modules: int | None = None,
    ) -> np.ndarray:
        """Add quiet zone around a sub-module expanded fusion matrix."""
        quiet = quiet_modules if quiet_modules is not None else self._config.quiet_zone_modules
        border_pixels = quiet * sub_module_factor
        padded_size = qr_module_size * sub_module_factor + border_pixels * 2
        padded = np.full((padded_size, padded_size), 255, dtype=matrix.dtype)
        padded[
            border_pixels : border_pixels + matrix.shape[0],
            border_pixels : border_pixels + matrix.shape[1],
        ] = matrix
        return padded

    def build_pixel_image(
        self,
        matrix: np.ndarray,
        *,
        qr_module_size: int,
        sub_module_factor: int = 1,
        physical_size_mm: float | None = None,
        module_scale: int | None = None,
        quiet_zone_modules: int | None = None,
        final_size: int | None = None,
    ) -> np.ndarray:
        """Build a full-resolution pixel image from a fusion matrix."""
        quiet = quiet_zone_modules if quiet_zone_modules is not None else self._config.quiet_zone_modules
        target = final_size if final_size is not None else self._config.final_size
        padded = self.add_quiet_zone_for_fusion(matrix, qr_module_size, sub_module_factor, quiet)

        if target > 0:
            pixel_scale = max(1, (target + padded.shape[0] - 1) // padded.shape[0])
            result = self.upscale_matrix(padded, pixel_scale)
            if result.shape[0] != target or result.shape[1] != target:
                result = resize(result, (target, target), nearest=True)
            return result

        size_mm = physical_size_mm if physical_size_mm is not None else self._config.physical_size_mm
        scale_per_qr_module = module_scale
        if scale_per_qr_module is None and size_mm > 0:
            total_modules = qr_module_size + quiet * 2
            target_pixels = int(round(size_mm / MM_PER_INCH * self._config.dpi))
            scale_per_qr_module = max(1, target_pixels // total_modules)
        if scale_per_qr_module is None:
            scale_per_qr_module = self._config.module_scale

        pixel_scale = max(1, scale_per_qr_module // sub_module_factor)
        return self.upscale_matrix(padded, pixel_scale)

    def upscale_matrix(self, matrix: np.ndarray, module_scale: int | None = None) -> np.ndarray:
        """Upscale each module to a square block of pixels."""
        scale = module_scale if module_scale is not None else self._config.module_scale
        return np.repeat(np.repeat(matrix, scale, axis=0), scale, axis=1)

    def render_fusion_png(
        self,
        matrix: np.ndarray,
        output_path: str | Path,
        *,
        qr_module_size: int,
        sub_module_factor: int = 1,
        physical_size_mm: float | None = None,
        dpi: int | None = None,
        quiet_zone_modules: int | None = None,
        module_scale: int | None = None,
        final_size: int | None = None,
    ) -> Path:
        """Render a fusion matrix with sub-module metadata to PNG."""
        target = final_size if final_size is not None else self._config.final_size
        pixel_matrix = self.build_pixel_image(
            matrix,
            qr_module_size=qr_module_size,
            sub_module_factor=sub_module_factor,
            physical_size_mm=physical_size_mm,
            module_scale=module_scale,
            quiet_zone_modules=quiet_zone_modules,
            final_size=target,
        )
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        render_dpi = dpi if dpi is not None else self._config.dpi
        image = Image.fromarray(pixel_matrix.astype(np.uint8), mode="L")
        image.save(output, format="PNG", dpi=(render_dpi, render_dpi))
        logger.info("Rendered fusion PNG: %s (%dx%d px, %d DPI)", output, image.width, image.height, render_dpi)
        return output

    def save_pixel_png(
        self,
        image: np.ndarray,
        output_path: str | Path,
        *,
        dpi: int | None = None,
    ) -> Path:
        """Write a ready-to-scan pixel image without module upscaling."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        render_dpi = dpi if dpi is not None else self._config.dpi
        pixel = image.astype(np.uint8)
        pil_image = Image.fromarray(pixel, mode="L")
        pil_image.save(output, format="PNG", dpi=(render_dpi, render_dpi))
        logger.info("Saved pixel PNG: %s (%dx%d px)", output, pil_image.width, pil_image.height)
        return output

    def render_png(
        self,
        matrix: np.ndarray,
        output_path: str | Path,
        *,
        physical_size_mm: float | None = None,
        dpi: int | None = None,
        quiet_zone_modules: int | None = None,
        module_scale: int | None = None,
    ) -> Path:
        """Render a grayscale module matrix to PNG with metadata.

        Args:
            matrix: Grayscale or binary module matrix.
            output_path: Destination PNG path.
            physical_size_mm: Optional override for physical output size.
            dpi: Optional override for output DPI.
            quiet_zone_modules: Optional override for quiet zone width.
            module_scale: Optional override for module pixel scale.

        Returns:
            Path to the written PNG file.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        render_dpi = dpi if dpi is not None else self._config.dpi
        quiet = quiet_zone_modules if quiet_zone_modules is not None else self._config.quiet_zone_modules
        size_mm = physical_size_mm if physical_size_mm is not None else self._config.physical_size_mm

        working = self.add_quiet_zone(matrix, quiet)
        scale = module_scale
        if scale is None and size_mm > 0:
            temp_config = RenderConfig(
                dpi=render_dpi,
                module_scale=self._config.module_scale,
                quiet_zone_modules=quiet,
                physical_size_mm=size_mm,
            )
            scale = ImageRenderEngine(temp_config).module_scale_for_physical_size(matrix, size_mm)
        if scale is None:
            scale = self._config.module_scale

        pixel_matrix = self.upscale_matrix(working, scale)
        image = Image.fromarray(pixel_matrix.astype(np.uint8), mode="L")
        image.save(output, format="PNG", dpi=(render_dpi, render_dpi))

        logger.info("Rendered PNG: %s (%dx%d px, %d DPI)", output, image.width, image.height, render_dpi)
        return output

    def render_comparison_strip(
        self,
        images: list[tuple[str, np.ndarray]],
        output_path: str | Path,
        *,
        dpi: int | None = None,
        gap_pixels: int = 16,
    ) -> Path:
        """Render labeled images side-by-side for visual comparison."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        render_dpi = dpi if dpi is not None else self._config.dpi

        pil_images = [Image.fromarray(img.astype(np.uint8), mode="L") for _, img in images]
        total_width = sum(img.width for img in pil_images) + gap_pixels * (len(pil_images) - 1)
        max_height = max(img.height for img in pil_images)

        canvas = Image.new("L", (total_width, max_height), color=255)
        x_offset = 0
        for pil_img in pil_images:
            canvas.paste(pil_img, (x_offset, 0))
            x_offset += pil_img.width + gap_pixels

        canvas.save(output, format="PNG", dpi=(render_dpi, render_dpi))
        logger.info("Rendered comparison strip: %s", output)
        return output
