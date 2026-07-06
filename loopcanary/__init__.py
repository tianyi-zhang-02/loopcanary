"""loopcanary — the pytest of agent-loop health.

A zero-infrastructure, in-process library that watches an agent loop from
inside the process and emits structured signals when the loop degrades.
No backend, no dashboard, no network I/O, no model calls — cheap enough to
run inside an RL rollout worker.

Public API::

    from loopcanary import Canary, LoopEvent, Signal, Severity, fingerprint

The full API is wired as the milestones land; see ``docs/`` and ``SCOPE.md``.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
