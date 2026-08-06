"""Unit tests for simulation engine."""

from __future__ import annotations

import numpy as np

from config import DistanceProfile, SimulationConfig
from simulation import SimulationEngine


def _checkerboard(size: int = 32) -> np.ndarray:
    grid = np.indices((size, size)).sum(axis=0) % 2
    return (grid * 255).astype(np.uint8)


def test_far_simulation_applies_more_blur_than_near() -> None:
    """Far profile should change pixels more aggressively than near profile."""
    engine = SimulationEngine(SimulationConfig(blur_level=3))
    source = _checkerboard()
    near = engine.simulate_near(source).image
    far = engine.simulate_far(source).image
    near_diff = np.mean(np.abs(near.astype(np.int16) - source.astype(np.int16)))
    far_diff = np.mean(np.abs(far.astype(np.int16) - source.astype(np.int16)))
    assert far_diff >= near_diff


def test_simulation_result_metadata() -> None:
    """Simulation result should expose profile and blur metadata."""
    engine = SimulationEngine()
    result = engine.simulate(_checkerboard(16), DistanceProfile.FAR)
    assert result.profile == DistanceProfile.FAR
    assert result.blur_level >= 1
