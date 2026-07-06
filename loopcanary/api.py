"""The in-process API — the primary door.

:class:`Canary` is the five-line way to instrument any loop you drive:

    from loopcanary import Canary

    canary = Canary()
    for step in agent_loop():
        for signal in canary.observe_raw(action=step.action, output=step.result):
            logger.warning(signal.message)

One ``Canary`` per loop (or per rollout). It is **not thread-safe** — that
is deliberate: locks would add cost to the per-event hot path, and the
intended usage is one instance per loop, which never shares state across
threads. If you run many loops in parallel (rollout workers), give each its
own ``Canary``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Set
from typing import Literal

from loopcanary.detectors import default_detectors
from loopcanary.protocol import Detector, Severity, Signal, fan_out
from loopcanary.schema import LoopEvent, ModelSignals, fingerprint

__all__ = ["Canary"]


class Canary:
    """Watch one agent loop from inside the process; emit signals on degradation."""

    def __init__(
        self,
        detectors: Iterable[Detector] | None = None,
        on_signal: Callable[[Signal], None] | None = None,
    ) -> None:
        """Create a Canary.

        Parameters
        ----------
        detectors:
            The detectors to run. Defaults to the three deterministic
            detectors at default thresholds (:func:`default_detectors`).
        on_signal:
            Optional callback invoked synchronously for each signal, in the
            order signals are produced. Use it to stream one-line alarms to a
            logger / stderr / Slack — the sink is yours.
        """
        self._detectors: list[Detector] = (
            list(detectors) if detectors is not None else default_detectors()
        )
        self._on_signal = on_signal
        self._step = -1  # observe_raw() auto-increments to 0 on first call
        # per-detector severity counts
        self._counts: dict[str, Counter[Severity]] = {}

    def observe(self, event: LoopEvent) -> list[Signal]:
        """Feed one fully-formed :class:`LoopEvent`; return signals it produced."""
        signals = fan_out(self._detectors, event)
        for s in signals:
            self._counts.setdefault(s.detector, Counter())[s.severity] += 1
            if self._on_signal is not None:
                self._on_signal(s)
        return signals

    def observe_raw(
        self,
        *,
        action: str | bytes | Mapping[str, object],
        output: str | bytes | Mapping[str, object],
        tokens: int | None = None,
        action_type: str = "action",
        action_volatile: Set[str] = frozenset(),
        output_volatile: Set[str] = frozenset(),
        metadata: Mapping[str, str] | None = None,
        model_signals: ModelSignals | None = None,
    ) -> list[Signal]:
        """Build a :class:`LoopEvent` from raw parts and observe it.

        Auto-increments the step counter, fingerprints ``action`` and
        ``output``, and timestamps the event. ``action_volatile`` and
        ``output_volatile`` strip caller-marked mapping keys such as
        timestamps or request IDs before hashing. This is the ergonomic path
        for loops that don't already produce ``LoopEvent`` objects.
        """
        self._step += 1
        event = LoopEvent(
            step=self._step,
            action_type=action_type,
            action_fingerprint=fingerprint(action, volatile=action_volatile),
            output_fingerprint=fingerprint(output, volatile=output_volatile),
            tokens_in_context=tokens,
            metadata=metadata,
            model_signals=model_signals,
        )
        return self.observe(event)

    def summary(self) -> dict[str, dict[str, int]]:
        """Per-detector signal counts by severity, for end-of-run logging.

        Returns ``{detector_name: {"INFO": n, "WARN": n, "ALERT": n,
        "total": n}}``. Detectors that never fired do not appear.
        """
        out: dict[str, dict[str, int]] = {}
        for name, counter in self._counts.items():
            info = counter.get(Severity.INFO, 0)
            warn = counter.get(Severity.WARN, 0)
            alert = counter.get(Severity.ALERT, 0)
            out[name] = {
                "INFO": info,
                "WARN": warn,
                "ALERT": alert,
                "total": info + warn + alert,
            }
        return out

    def reset(self) -> None:
        """Clear all detector state and counters for a fresh run."""
        for d in self._detectors:
            d.reset()
        self._step = -1
        self._counts.clear()

    def __enter__(self) -> Canary:
        self.reset()
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        return False
