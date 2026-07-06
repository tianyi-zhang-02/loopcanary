"""Detector protocol, signal type, and the cascade fan-out.

A detector consumes **events or signals** and emits **signals**. The cheap
deterministic detectors (v1) consume events. The cascade interface — the
one thing that makes a cheap-filter → expensive-confirm pipeline buildable
rather than a refactor — lets a *second-stage* detector (an LLM judge, a
learned probe; both third-party in v1) consume the signals the first stage
emitted, and confirm or enrich them.

The fan-out (:func:`fan_out`) is deliberately tiny and legible: an event is
offered to every event-consuming detector; the signals they emit are then
offered to every signal-consuming detector. One bounded cascade level, no
recursion, no magic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Protocol, runtime_checkable

from loopcanary.schema import LoopEvent

__all__ = ["Severity", "Signal", "Detector", "fan_out"]


class Severity(IntEnum):
    """Signal severity. Ordered so ``severity >= Severity.WARN`` works."""

    INFO = 10
    WARN = 20
    ALERT = 30


@dataclass(frozen=True)
class Signal:
    """A structured, named detection. Legible, not a composite score."""

    detector: str
    severity: Severity
    step: int
    pattern: str
    message: str
    evidence: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class Detector(Protocol):
    """A detector consumes events (and/or signals) and emits signals.

    Implementations expose:

    * ``name`` — stable identifier used in ``Signal.detector`` and summaries.
    * ``consumes`` — a frozenset of ``{"event"}`` and/or ``{"signal"}``.
      Defaults to ``{"event"}`` for the deterministic detectors. A
      second-stage detector sets ``{"signal"}`` (or both).
    * ``consume(item)`` — offered one ``LoopEvent`` or ``Signal``; returns a
      (possibly empty) list of new signals. Must be cheap and deterministic.
    * ``reset()`` — clear all internal state for a fresh run.
    """

    name: str
    consumes: frozenset[str]

    def consume(self, item: LoopEvent | Signal) -> list[Signal]: ...

    def reset(self) -> None: ...


def fan_out(detectors: Iterable[Detector], event: LoopEvent) -> list[Signal]:
    """Run one event through the detector cascade; return all signals.

    Stage 1: offer ``event`` to every detector that consumes ``"event"``.
    Stage 2: offer each stage-1 signal to every detector that consumes
    ``"signal"``. Bounded at one cascade level — a signal-consumer's own
    output is returned but not re-fanned, which keeps the mechanism finite
    and legible.
    """
    detectors = list(detectors)
    signals: list[Signal] = []

    for det in detectors:
        if "event" in det.consumes:
            signals.extend(det.consume(event))

    second_stage: list[Signal] = []
    signal_consumers = [d for d in detectors if "signal" in d.consumes]
    if signal_consumers:
        for sig in signals:
            for det in signal_consumers:
                second_stage.extend(det.consume(sig))

    signals.extend(second_stage)
    return signals
