"""CLI entry point for the dual-information QR fusion platform."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import (  # noqa: E402
    ALLOWED_DPI_VALUES,
    AppConfig,
    DEFAULT_DPI,
    DEFAULT_FINAL_SIZE,
    DistanceProfile,
    MAX_FINAL_SIZE,
    MAX_GRAY_VALUE,
    MIN_FINAL_SIZE,
    MIN_GRAY_VALUE,
    OUTPUT_PRESET_MANUAL,
    OUTPUT_PRESETS,
    apply_output_preset,
    load_default_config,
)
from dual_info_qr import recover_near_matrix_from_dual, resolve_dual_info_sizes  # noqa: E402
from fusion_adaptation import prepare_config_for_payloads  # noqa: E402
from image_renderer import ImageRenderEngine  # noqa: E402
from matrix_fusion import MatrixFusionEngine  # noqa: E402
from qr_generator import QRLayerGenerator  # noqa: E402
from simulation import SimulationEngine  # noqa: E402
from validator import FusionValidator, LayerRecoveryEngine  # noqa: E402

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(verbose: bool) -> None:
    """Configure root logger for CLI execution."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)


def build_config_from_args(args: argparse.Namespace) -> AppConfig:
    """Merge CLI arguments into application configuration."""
    config = load_default_config()
    config.url_a = args.url_a
    config.url_b = args.url_b
    config.output_dir = args.output_dir

    preset_ids = [preset.id for preset in OUTPUT_PRESETS] + [OUTPUT_PRESET_MANUAL]
    if args.output_preset not in preset_ids:
        raise ValueError(f"output_preset must be one of {preset_ids}")
    apply_output_preset(config, args.output_preset)

    if args.output_preset == OUTPUT_PRESET_MANUAL:
        config.render.dpi = args.dpi
        config.render.final_size = args.final_size
        config.render.physical_size_mm = args.physical_size_mm
        config.fusion.module_block_size = args.module_block_size
        config.fusion.centroid_size = args.centroid_size
        config.fusion.auto_tune = False

    if not MIN_FINAL_SIZE <= config.render.final_size <= MAX_FINAL_SIZE:
        raise ValueError(
            f"final_size must be between {MIN_FINAL_SIZE} and {MAX_FINAL_SIZE}, got {config.render.final_size}",
        )
    config.render.module_scale = args.module_scale
    config.render.quiet_zone_modules = args.quiet_zone
    config.simulation.blur_level = args.blur_level
    config.simulation.distance_profile = DistanceProfile(args.distance_profile)
    return config


def run_pipeline(config: AppConfig) -> Path:
    """Execute the full pipeline and return the fused PNG path."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prepare_config_for_payloads(config, config.url_a, config.url_b)

    layer_generator = QRLayerGenerator(config.qr_a, config.qr_b)
    matrix_a = layer_generator.generate_layer_a(config.url_a)
    matrix_b = layer_generator.generate_layer_b(config.url_b)

    fusion_engine = MatrixFusionEngine(config.fusion, final_size=config.render.final_size)
    fusion_result = fusion_engine.fuse(matrix_a, matrix_b)

    m, omega = resolve_dual_info_sizes(
        fusion_result.qr_module_size,
        config.render.final_size,
        config.fusion.module_block_size,
        config.fusion.centroid_size,
    )
    recovered_b_bool = recover_near_matrix_from_dual(
        fusion_result.matrix, fusion_result.qr_module_size, m, omega
    )
    recovered_b = recovered_b_bool.astype(np.uint8) * MIN_GRAY_VALUE + (~recovered_b_bool).astype(np.uint8) * MAX_GRAY_VALUE

    renderer = ImageRenderEngine(config.render)
    fused_png = renderer.render_fusion_png(
        fusion_result.matrix,
        output_dir / "fused_qr.png",
        qr_module_size=fusion_result.qr_module_size,
        sub_module_factor=fusion_result.sub_module_factor,
        dpi=config.render.dpi,
        final_size=config.render.final_size,
    )

    recovery_engine = LayerRecoveryEngine()
    near_decode_ready = recovery_engine.matrix_to_decode_image(recovered_b)
    canvas = np.full((config.render.final_size, config.render.final_size), 255, dtype=np.uint8)
    offset_y = max(0, (config.render.final_size - near_decode_ready.shape[0]) // 2)
    offset_x = max(0, (config.render.final_size - near_decode_ready.shape[1]) // 2)
    height = min(near_decode_ready.shape[0], config.render.final_size - offset_y)
    width = min(near_decode_ready.shape[1], config.render.final_size - offset_x)
    canvas[offset_y : offset_y + height, offset_x : offset_x + width] = near_decode_ready[:height, :width]
    near_pixels = canvas

    near_png = renderer.save_pixel_png(
        near_pixels,
        output_dir / "fused_qr_near.png",
        dpi=config.render.dpi,
    )

    pixel_fused = renderer.build_pixel_image(
        fusion_result.matrix,
        qr_module_size=fusion_result.qr_module_size,
        sub_module_factor=fusion_result.sub_module_factor,
        final_size=config.render.final_size,
    )

    simulation_engine = SimulationEngine(config.simulation)
    simulation_engine.save_simulation_outputs(
        pixel_fused,
        output_dir,
        renderer,
        near_base_image=near_pixels,
    )

    validator = FusionValidator(
        expected_url_a=config.url_a,
        expected_url_b=config.url_b,
        simulation_config=config.simulation,
        render_config=config.render,
        sub_module_factor=fusion_result.sub_module_factor,
        fusion_centroid_size=omega,
        qr_version=config.qr_a.version,
        output_preset=config.output_preset,
    )
    validator.validate_fused_image(
        pixel_fused,
        output_dir,
        fusion_matrix=fusion_result.matrix,
        qr_module_size=fusion_result.qr_module_size,
        near_scan_image=near_pixels,
        distance_profile=config.simulation.distance_profile,
    )

    logging.getLogger(__name__).info("Pipeline completed. Output: %s (near ref: %s)", output_dir, near_png)
    return fused_png


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    preset_help = ", ".join(preset.id for preset in OUTPUT_PRESETS)
    parser = argparse.ArgumentParser(
        description="Dual-information QR fusion — one code, two URLs by scan distance.",
    )
    parser.add_argument("--url-a", default="https://example.com/marketing", help="Far-range URL (QR-A)")
    parser.add_argument("--url-b", default="https://example.com/verify/token-001", help="Near-range URL (QR-B)")
    parser.add_argument("--output-dir", default="output", help="Directory for generated artifacts")
    parser.add_argument(
        "--output-preset",
        choices=[preset.id for preset in OUTPUT_PRESETS] + [OUTPUT_PRESET_MANUAL],
        default="a4_print",
        help=f"Output preset ({preset_help}, {OUTPUT_PRESET_MANUAL})",
    )
    parser.add_argument(
        "--module-block-size",
        type=int,
        default=None,
        help="Module block size m (manual preset only; 7–29)",
    )
    parser.add_argument(
        "--centroid-size",
        type=int,
        default=None,
        help="Centroid size ω (manual preset only; suggest m/3)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        choices=list(ALLOWED_DPI_VALUES),
        default=DEFAULT_DPI,
        help=f"Output PNG DPI ({', '.join(str(v) for v in ALLOWED_DPI_VALUES)})",
    )
    parser.add_argument(
        "--final-size",
        type=int,
        default=DEFAULT_FINAL_SIZE,
        help=f"Final output pixel size ({MIN_FINAL_SIZE}-{MAX_FINAL_SIZE})",
    )
    parser.add_argument("--module-scale", type=int, default=10, help="Fallback module pixel scale")
    parser.add_argument("--quiet-zone", type=int, default=4, help="Quiet zone width in modules")
    parser.add_argument("--physical-size-mm", type=float, default=40.0, help="Target physical QR size in mm")
    parser.add_argument("--blur-level", type=int, default=3, help="Base blur level for simulation")
    parser.add_argument(
        "--distance-profile",
        choices=[profile.value for profile in DistanceProfile],
        default=DistanceProfile.FAR.value,
        help="Primary distance profile for validation reporting",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point."""
    args = parse_args(argv)
    configure_logging(args.verbose)
    config = build_config_from_args(args)
    run_pipeline(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
