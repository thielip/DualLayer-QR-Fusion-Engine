"""Scan-distance and print/scanner distortion simulation engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from config import (
    DistanceProfile,
    FAR_BLUR_KERNEL,
    FAR_DOWNSCALE_FACTOR,
    NEAR_BLUR_KERNEL,
    NEAR_DOWNSCALE_FACTOR,
    NEAR_SCANNER_BRIGHTNESS_BETA,
    NEAR_SCANNER_CONTRAST_ALPHA,
    PRINT_NOISE_STD,
    SCANNER_BRIGHTNESS_BETA,
    SCANNER_CONTRAST_ALPHA,
    SimulationConfig,
)
from image_renderer import ImageRenderEngine
from imgops import convert_scale, gaussian_blur, resize

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationResult:
    """Container for a single simulation output."""

    profile: DistanceProfile
    image: np.ndarray
    blur_level: int
    downscale_factor: float


class SimulationEngine:
    """Simulate near/far scanning and reproduction artifacts."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        """Initialize simulation engine."""
        self._config = config or SimulationConfig()

    @property
    def config(self) -> SimulationConfig:
        """Return active simulation configuration."""
        return self._config

    def _resolve_blur_kernel(self, profile: DistanceProfile, blur_level: int | None) -> int:
        """Map profile and blur level to an odd Gaussian kernel size."""
        if blur_level is not None:
            kernel = max(1, blur_level)
        elif profile == DistanceProfile.NEAR:
            kernel = NEAR_BLUR_KERNEL
        else:
            kernel = FAR_BLUR_KERNEL
        return kernel if kernel % 2 == 1 else kernel + 1

    def _resolve_downscale(self, profile: DistanceProfile) -> float:
        """Resolve downscale factor from profile or explicit override."""
        if self._config.downscale_factor is not None:
            return self._config.downscale_factor
        if profile == DistanceProfile.NEAR:
            return NEAR_DOWNSCALE_FACTOR
        return FAR_DOWNSCALE_FACTOR

    def apply_gaussian_blur(self, image: np.ndarray, kernel_size: int, sigma: float | None = None) -> np.ndarray:
        """Apply Gaussian blur to emulate optical defocus."""
        if kernel_size <= 1:
            return image.copy()
        resolved_sigma = sigma if sigma is not None else self._config.gaussian_sigma
        if resolved_sigma is None:
            resolved_sigma = kernel_size / 3.0
        return gaussian_blur(image, kernel_size, float(resolved_sigma))

    def apply_resolution_loss(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Downscale and upscale to emulate limited resolving power."""
        if factor >= 1.0:
            return image.copy()
        height, width = image.shape[:2]
        small_w = max(1, int(width * factor))
        small_h = max(1, int(height * factor))
        reduced = resize(image, (small_w, small_h), nearest=False)
        return resize(reduced, (width, height), nearest=False)

    def apply_print_distortion(self, image: np.ndarray) -> np.ndarray:
        """Add mild print noise and slight gamma drift."""
        noisy = image.astype(np.float32)
        noise = np.random.default_rng(0).normal(0.0, PRINT_NOISE_STD, size=image.shape)
        return np.clip(noisy + noise, 0, 255).astype(np.uint8)

    def apply_scanner_distortion(self, image: np.ndarray, profile: DistanceProfile | None = None) -> np.ndarray:
        """Apply contrast/brightness shifts typical of CMOS scanners."""
        if profile == DistanceProfile.NEAR:
            alpha = NEAR_SCANNER_CONTRAST_ALPHA
            beta = NEAR_SCANNER_BRIGHTNESS_BETA
        else:
            alpha = SCANNER_CONTRAST_ALPHA
            beta = SCANNER_BRIGHTNESS_BETA
        return convert_scale(image, alpha=alpha, beta=beta)

    def simulate(
        self,
        image: np.ndarray,
        profile: DistanceProfile | None = None,
        blur_level: int | None = None,
    ) -> SimulationResult:
        """Run a full simulation pipeline for the given distance profile."""
        active_profile = profile or self._config.distance_profile
        active_blur = blur_level if blur_level is not None else self._config.blur_level
        kernel = self._resolve_blur_kernel(active_profile, active_blur)
        factor = self._resolve_downscale(active_profile)

        logger.info(
            "Simulating profile=%s blur=%d downscale=%.2f",
            active_profile.value,
            kernel,
            factor,
        )

        result = image.copy()
        result = self.apply_resolution_loss(result, factor)
        result = self.apply_gaussian_blur(result, kernel)
        if self._config.apply_print_distortion:
            result = self.apply_print_distortion(result)
        if self._config.apply_scanner_distortion:
            result = self.apply_scanner_distortion(result, active_profile)

        return SimulationResult(
            profile=active_profile,
            image=result,
            blur_level=kernel,
            downscale_factor=factor,
        )

    def simulate_near(self, image: np.ndarray, blur_level: int | None = None) -> SimulationResult:
        """Simulate close-range scanning conditions."""
        return self.simulate(image, DistanceProfile.NEAR, blur_level)

    def simulate_far(self, image: np.ndarray, blur_level: int | None = None) -> SimulationResult:
        """Simulate long-range scanning conditions."""
        return self.simulate(image, DistanceProfile.FAR, blur_level)

    def save_simulation_outputs(
        self,
        base_image: np.ndarray,
        output_dir: str | Path,
        renderer: ImageRenderEngine | None = None,
        *,
        near_base_image: np.ndarray | None = None,
    ) -> dict[str, Path]:
        """Generate near/far simulations and a comparison strip."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        render_engine = renderer or ImageRenderEngine()

        far = self.simulate_far(base_image)
        near_source = near_base_image if near_base_image is not None else base_image
        near = self.simulate_near(near_source)
        near_display = near.image

        paths = {
            "near": render_engine.render_png(near_display, output_path / "simulation_near.png"),
            "near_raw": render_engine.render_png(near.image, output_path / "simulation_near_raw.png"),
            "far": render_engine.render_png(far.image, output_path / "simulation_far.png"),
        }
        paths["comparison"] = render_engine.render_comparison_strip(
            [
                ("original_far", base_image),
                ("near_b", near_display),
                ("far", far.image),
            ],
            output_path / "simulation_comparison.png",
        )
        return paths
