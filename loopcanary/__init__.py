"""loopcanary — the pytest of agent-loop health.

A zero-infrastructure, in-process library that watches an agent loop from
inside the process and emits structured signals when the loop degrades.
No backend, no dashboard, no network I/O, no model calls — cheap enough to
run inside an RL rollout worker.

Public API::

    from loopcanary import Canary, LoopEvent, Signal, Severity, fingerprint
"""

from __future__ import annotations

from loopcanary.api import Canary
from loopcanary.protocol import Detector, Severity, Signal
from loopcanary.schema import LoopEvent, ModelSignals, fingerprint

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Canary",
    "LoopEvent",
    "ModelSignals",
    "Signal",
    "Severity",
    "Detector",
    "fingerprint",
]
