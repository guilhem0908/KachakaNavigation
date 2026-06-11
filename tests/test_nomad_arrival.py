"""Arrival-detection logic tests that need no torch/checkpoint."""
from __future__ import annotations

from pathlib import Path

import pytest

from kachaka_navigation.models.nomad_original import (
    NomadOriginalConfig,
    NomadOriginalModel,
)


def _config(**overrides):
    return NomadOriginalConfig(checkpoint_path=Path("unused.pth"), **overrides)


def test_fixed_similarity_threshold_is_used_directly():
    model = NomadOriginalModel(_config(goal_similarity_threshold=0.9))
    assert model._resolve_similarity_threshold(0.2) == 0.9
    assert model._resolve_similarity_threshold(0.95) == 0.9


def test_auto_calibration_builds_threshold_from_start_baseline():
    model = NomadOriginalModel(
        _config(goal_similarity_margin=0.5, goal_similarity_baseline_frames=3)
    )
    # Calibration window: no threshold yet, similarity cannot fire.
    assert model._resolve_similarity_threshold(0.5) is None
    assert model._resolve_similarity_threshold(0.6) is None
    assert model._resolve_similarity_threshold(0.4) is None  # 3rd: calibrates
    # Median baseline 0.5 -> threshold = 0.5 + 0.5 * (1 - 0.5) = 0.75
    assert model._resolve_similarity_threshold(0.9) == pytest.approx(0.75)
    # Threshold is now stable regardless of later readings.
    assert model._resolve_similarity_threshold(0.1) == pytest.approx(0.75)


def test_auto_calibration_adapts_to_start_position():
    # Start view already similar to the goal -> higher threshold.
    near = NomadOriginalModel(
        _config(goal_similarity_margin=0.5, goal_similarity_baseline_frames=1)
    )
    near._resolve_similarity_threshold(0.8)
    assert near._resolve_similarity_threshold(0.0) == pytest.approx(0.9)

    # Start view unrelated to the goal -> lower threshold.
    far = NomadOriginalModel(
        _config(goal_similarity_margin=0.5, goal_similarity_baseline_frames=1)
    )
    far._resolve_similarity_threshold(0.2)
    assert far._resolve_similarity_threshold(0.0) == pytest.approx(0.6)


def test_reset_clears_auto_calibration():
    model = NomadOriginalModel(
        _config(goal_similarity_margin=0.5, goal_similarity_baseline_frames=1)
    )
    model._resolve_similarity_threshold(0.5)
    assert model._resolve_similarity_threshold(0.0) is not None
    model.reset()
    # Back in the calibration window after reset.
    assert model._resolve_similarity_threshold(0.5) is None


def test_bearing_filter_requires_consecutive_trusted_readings():
    model = NomadOriginalModel(
        _config(goal_bearing_patience=2, goal_bearing_smoothing=1.0)
    )
    assert model._update_bearing_filter(0.2, trusted=True) is None  # streak 1
    assert model._update_bearing_filter(0.2, trusted=True) == pytest.approx(0.2)
    # An untrusted reading resets the streak and the smoothing.
    assert model._update_bearing_filter(0.2, trusted=False) is None
    assert model._update_bearing_filter(0.2, trusted=True) is None


def test_bearing_filter_smooths_measurements():
    model = NomadOriginalModel(
        _config(goal_bearing_patience=1, goal_bearing_smoothing=0.5,
                goal_bearing_deadband_deg=0.001)
    )
    assert model._update_bearing_filter(0.4, trusted=True) == pytest.approx(0.4)
    # EMA: 0.5 * 0.0 + 0.5 * 0.4 = 0.2 — a sudden flip is damped, not applied raw.
    assert model._update_bearing_filter(0.0, trusted=True) == pytest.approx(0.2)


def test_bearing_filter_deadband_yields_exactly_straight():
    import math

    model = NomadOriginalModel(
        _config(goal_bearing_patience=1, goal_bearing_deadband_deg=3.0)
    )
    small = math.radians(2.0)
    assert model._update_bearing_filter(small, trusted=True) == 0.0
    model.reset()
    large = math.radians(8.0)
    assert model._update_bearing_filter(large, trusted=True) == pytest.approx(large)


def test_config_validation_rejects_bad_similarity_settings():
    with pytest.raises(ValueError):
        _config(goal_similarity_threshold=1.5)
    with pytest.raises(ValueError):
        _config(goal_similarity_margin=0.0)
    with pytest.raises(ValueError):
        _config(goal_similarity_baseline_frames=0)
    with pytest.raises(ValueError):
        _config(arrival_detector="bogus")
