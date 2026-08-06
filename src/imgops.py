"""Lightweight image helpers (Pillow/NumPy) — no OpenCV dependency for Cloud."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def read_gray(path: str | bytes) -> np.ndarray | None:
    """Read an image file as uint8 grayscale, or None if missing/unreadable."""
    try:
        with Image.open(path) as img:
            return np.asarray(ImageOps.exif_transpose(img).convert("L"), dtype=np.uint8)
    except OSError:
        return None


def resize(image: np.ndarray, size: tuple[int, int], *, nearest: bool = False) -> np.ndarray:
    """Resize a grayscale or RGB uint8 image to (width, height)."""
    if nearest:
        resample = Image.Resampling.NEAREST
    elif image.shape[0] * image.shape[1] > size[0] * size[1]:
        resample = Image.Resampling.BOX
    else:
        resample = Image.Resampling.BILINEAR
    pil = Image.fromarray(image)
    return np.asarray(pil.resize(size, resample=resample), dtype=np.uint8)


def gaussian_blur(image: np.ndarray, kernel_size: int, sigma: float = 0.0) -> np.ndarray:
    """Approximate OpenCV GaussianBlur with Pillow."""
    radius = max(0.5, (kernel_size if sigma <= 0 else sigma * 2.0) / 2.0)
    pil = Image.fromarray(image).filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(pil, dtype=np.uint8)


def convert_scale(image: np.ndarray, *, alpha: float, beta: float) -> np.ndarray:
    """Match cv2.convertScaleAbs contrast/brightness."""
    scaled = image.astype(np.float32) * float(alpha) + float(beta)
    return np.clip(scaled, 0, 255).astype(np.uint8)


def threshold_binary(image: np.ndarray, threshold: int) -> np.ndarray:
    """Binary threshold to 0/255."""
    return np.where(image > threshold, 255, 0).astype(np.uint8)


def threshold_otsu(image: np.ndarray) -> np.ndarray:
    """Otsu-like threshold using histogram (grayscale)."""
    hist, _ = np.histogram(image.ravel(), bins=256, range=(0, 256))
    total = image.size
    sum_total = np.dot(np.arange(256), hist)
    sum_b = 0.0
    weight_b = 0.0
    max_var = -1.0
    threshold = 128
    for t in range(256):
        weight_b += hist[t]
        if weight_b == 0:
            continue
        weight_f = total - weight_b
        if weight_f == 0:
            break
        sum_b += t * hist[t]
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / weight_f
        var_between = weight_b * weight_f * (mean_b - mean_f) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = t
    return threshold_binary(image, threshold)


def gray_to_rgb(image: np.ndarray) -> np.ndarray:
    """Stack grayscale to RGB."""
    if image.ndim == 3:
        return image
    return np.stack([image, image, image], axis=-1)
