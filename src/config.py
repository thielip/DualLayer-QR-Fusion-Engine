"""Central configuration for the dual-information QR fusion platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final


FUSION_MODE: Final[str] = "dual_info"
OUTPUT_PRESET_MANUAL: Final[str] = "manual"


class DistanceProfile(str, Enum):
    """Scan distance simulation profiles."""

    NEAR = "near"
    FAR = "far"


class ErrorCorrectionLevel(str, Enum):
    """QR error correction levels mapped to qrcode constants."""

    L = "L"
    M = "M"
    Q = "Q"
    H = "H"


# --- Physical / rendering defaults ---
DEFAULT_DPI: Final[int] = 600
ALLOWED_DPI_VALUES: Final[tuple[int, ...]] = (300, 600, 1200, 2400)
DEFAULT_MODULE_SCALE: Final[int] = 10
DEFAULT_QUIET_ZONE_MODULES: Final[int] = 4
DEFAULT_PHYSICAL_SIZE_MM: Final[float] = 40.0
DEFAULT_FINAL_SIZE: Final[int] = 1200
MIN_FINAL_SIZE: Final[int] = 1200
MAX_FINAL_SIZE: Final[int] = 6400
FINAL_SIZE_STEP: Final[int] = 100

# --- Dual-info fusion defaults ---
DEFAULT_MODULE_BLOCK_SIZE: Final[int] = 11
DEFAULT_CENTROID_SIZE: Final[int] = 3
MIN_GRAY_VALUE: Final[int] = 0
MAX_GRAY_VALUE: Final[int] = 255

# --- Simulation defaults ---
DEFAULT_BLUR_LEVEL: Final[int] = 3
DEFAULT_DISTANCE_PROFILE: Final[DistanceProfile] = DistanceProfile.FAR
NEAR_BLUR_KERNEL: Final[int] = 1
FAR_BLUR_KERNEL: Final[int] = 5
NEAR_DOWNSCALE_FACTOR: Final[float] = 1.0
FAR_DOWNSCALE_FACTOR: Final[float] = 0.35
PRINT_NOISE_STD: Final[float] = 4.0
SCANNER_CONTRAST_ALPHA: Final[float] = 1.1
SCANNER_BRIGHTNESS_BETA: Final[int] = -5
NEAR_SCANNER_CONTRAST_ALPHA: Final[float] = 1.25
NEAR_SCANNER_BRIGHTNESS_BETA: Final[int] = 8

# --- Validation ---
VALIDATION_REPORT_FILENAME: Final[str] = "validation_report.json"
FAR_BINARIZE_THRESHOLD: Final[int] = 200
NEAR_BINARIZE_THRESHOLD: Final[int] = 118
FINDER_PATTERN_SIZE: Final[int] = 7
FINDER_SEPARATOR_BORDER: Final[int] = 9
TIMING_PATTERN_ROW: Final[int] = 6
TIMING_PATTERN_COL: Final[int] = 6
MIN_QR_VERSION_SIZE: Final[int] = 21
VERSION_INFO_THRESHOLD: Final[int] = 7

@dataclass(frozen=True)
class OutputPreset:
    """Named output parameter bundle for common use cases."""

    id: str
    label: str
    final_size: int
    dpi: int
    module_block_size: int | None
    centroid_size: int | None
    physical_size_mm: float
    auto_tune: bool


OUTPUT_PRESETS: Final[tuple[OutputPreset, ...]] = (
    OutputPreset(
        id="screen",
        label="螢幕展示（論文 Fig.9）",
        final_size=1200,
        dpi=300,
        module_block_size=11,
        centroid_size=3,
        physical_size_mm=40.0,
        auto_tune=False,
    ),
    OutputPreset(
        id="a4_print",
        label="A4 標準列印（4×4 cm）",
        final_size=1200,
        dpi=600,
        module_block_size=None,
        centroid_size=None,
        physical_size_mm=40.0,
        auto_tune=True,
    ),
    OutputPreset(
        id="hi_res",
        label="高解析列印",
        final_size=2400,
        dpi=1200,
        module_block_size=None,
        centroid_size=None,
        physical_size_mm=40.0,
        auto_tune=True,
    ),
    OutputPreset(
        id="large",
        label="大尺寸輸出（6×6 cm）",
        final_size=3200,
        dpi=2400,
        module_block_size=None,
        centroid_size=None,
        physical_size_mm=60.0,
        auto_tune=True,
    ),
)


def get_output_preset(preset_id: str) -> OutputPreset | None:
    """Return a preset by id, or None if not found."""
    for preset in OUTPUT_PRESETS:
        if preset.id == preset_id:
            return preset
    return None


@dataclass
class QRGeneratorConfig:
    """Parameters for standard QR matrix generation."""

    error_correction: ErrorCorrectionLevel = ErrorCorrectionLevel.M
    version: int | None = None
    border: int = 0


@dataclass
class FusionConfig:
    """Parameters for dual-information matrix fusion."""

    module_block_size: int | None = None
    centroid_size: int | None = None
    auto_tune: bool = True


@dataclass
class RenderConfig:
    """Parameters for PNG rendering."""

    dpi: int = DEFAULT_DPI
    final_size: int = DEFAULT_FINAL_SIZE
    module_scale: int = DEFAULT_MODULE_SCALE
    quiet_zone_modules: int = DEFAULT_QUIET_ZONE_MODULES
    physical_size_mm: float = DEFAULT_PHYSICAL_SIZE_MM

    def __post_init__(self) -> None:
        """Validate render parameters."""
        if self.dpi not in ALLOWED_DPI_VALUES:
            raise ValueError(f"dpi must be one of {ALLOWED_DPI_VALUES}, got {self.dpi}")
        if not MIN_FINAL_SIZE <= self.final_size <= MAX_FINAL_SIZE:
            raise ValueError(
                f"final_size must be between {MIN_FINAL_SIZE} and {MAX_FINAL_SIZE}, got {self.final_size}",
            )


@dataclass
class SimulationConfig:
    """Parameters for scan-distance simulation."""

    blur_level: int = DEFAULT_BLUR_LEVEL
    distance_profile: DistanceProfile = DEFAULT_DISTANCE_PROFILE
    downscale_factor: float | None = None
    apply_print_distortion: bool = True
    apply_scanner_distortion: bool = True
    gaussian_sigma: float | None = None


@dataclass
class AppConfig:
    """Top-level application configuration."""

    url_a: str = "https://example.com/marketing"
    url_b: str = "https://example.com/verify/token-001"
    output_preset: str = "a4_print"
    qr_a: QRGeneratorConfig = field(
        default_factory=lambda: QRGeneratorConfig(error_correction=ErrorCorrectionLevel.L)
    )
    qr_b: QRGeneratorConfig = field(
        default_factory=lambda: QRGeneratorConfig(error_correction=ErrorCorrectionLevel.L)
    )
    fusion: FusionConfig = field(default_factory=FusionConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    output_dir: str = "output"


def apply_output_preset(config: AppConfig, preset_id: str) -> None:
    """Apply a named output preset to render/fusion settings."""
    if preset_id == OUTPUT_PRESET_MANUAL:
        config.output_preset = OUTPUT_PRESET_MANUAL
        config.fusion.auto_tune = False
        return

    preset = get_output_preset(preset_id)
    if preset is None:
        raise ValueError(f"Unknown output preset: {preset_id}")

    config.output_preset = preset.id
    config.render.final_size = preset.final_size
    config.render.dpi = preset.dpi
    config.render.physical_size_mm = preset.physical_size_mm
    config.fusion.module_block_size = preset.module_block_size
    config.fusion.centroid_size = preset.centroid_size
    config.fusion.auto_tune = preset.auto_tune


def load_default_config() -> AppConfig:
    """Return the default application configuration."""
    config = AppConfig()
    apply_output_preset(config, config.output_preset)
    return config
