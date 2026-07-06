"""Deterministic detectors — the always-on first layer.

All three are O(1)-ish per event, bounded-memory (sliding windows), and
deterministic given the same event stream. They make no model calls and
touch no network — cheap enough for a rollout worker.

``default_detectors()`` returns a fresh instance of each with default
thresholds, which is what :class:`loopcanary.api.Canary` uses when no
detectors are supplied.
"""

from __future__ import annotations

from loopcanary.detectors.context_pressure import ContextPressure
from loopcanary.detectors.null_progress import NullProgress
from loopcanary.detectors.repeated_action import RepeatedAction
from loopcanary.protocol import Detector

__all__ = ["RepeatedAction", "NullProgress", "ContextPressure", "default_detectors"]


def default_detectors() -> list[Detector]:
    """A fresh list of the three deterministic detectors at default thresholds."""
    return [RepeatedAction(), NullProgress(), ContextPressure()]
