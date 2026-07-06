"""Tests for the detector protocol, Signal/Severity, and cascade fan-out."""

from __future__ import annotations

from loopcanary.protocol import Detector, Severity, Signal, fan_out
from loopcanary.schema import LoopEvent, fingerprint


def _event(step: int, action: str = "a", output: str = "o") -> LoopEvent:
    return LoopEvent(
        step=step,
        action_type="tool:test",
        action_fingerprint=fingerprint(action),
        output_fingerprint=fingerprint(output),
    )


# ---------------------------------------------------------------------------
# Severity / Signal
# ---------------------------------------------------------------------------


def test_severity_is_ordered() -> None:
    assert Severity.INFO < Severity.WARN < Severity.ALERT
    assert Severity.ALERT >= Severity.WARN


def test_signal_defaults_empty_evidence() -> None:
    s = Signal(detector="d", severity=Severity.WARN, step=1, pattern="p", message="m")
    assert s.evidence == {}


# ---------------------------------------------------------------------------
# Dummy detectors exercising the protocol + cascade
# ---------------------------------------------------------------------------


class _EventDetector:
    """Fires an INFO signal on every event."""

    name = "event_det"
    consumes = frozenset({"event"})

    def __init__(self) -> None:
        self.seen = 0

    def consume(self, item: LoopEvent | Signal) -> list[Signal]:
        assert isinstance(item, LoopEvent)
        self.seen += 1
        return [
            Signal(
                detector=self.name,
                severity=Severity.INFO,
                step=item.step,
                pattern="saw_event",
                message="saw an event",
            )
        ]

    def reset(self) -> None:
        self.seen = 0


class _SignalDetector:
    """Second-stage: consumes signals, escalates them to WARN."""

    name = "signal_det"
    consumes = frozenset({"signal"})

    def __init__(self) -> None:
        self.seen: list[Signal] = []

    def consume(self, item: LoopEvent | Signal) -> list[Signal]:
        assert isinstance(item, Signal)
        self.seen.append(item)
        return [
            Signal(
                detector=self.name,
                severity=Severity.WARN,
                step=item.step,
                pattern="confirmed",
                message=f"confirmed {item.pattern}",
                evidence={"upstream": item.detector},
            )
        ]

    def reset(self) -> None:
        self.seen = []


def test_dummy_detectors_satisfy_protocol() -> None:
    assert isinstance(_EventDetector(), Detector)
    assert isinstance(_SignalDetector(), Detector)


def test_fan_out_event_only() -> None:
    det = _EventDetector()
    signals = fan_out([det], _event(0))
    assert det.seen == 1
    assert len(signals) == 1
    assert signals[0].detector == "event_det"


def test_fan_out_cascade_signal_consumer_receives_signals() -> None:
    ev, sig = _EventDetector(), _SignalDetector()
    signals = fan_out([ev, sig], _event(5))
    # stage 1: one INFO from the event detector; stage 2: one WARN from the
    # signal detector confirming it.
    kinds = {(s.detector, s.severity) for s in signals}
    assert ("event_det", Severity.INFO) in kinds
    assert ("signal_det", Severity.WARN) in kinds
    assert len(sig.seen) == 1
    assert sig.seen[0].detector == "event_det"


def test_fan_out_signal_consumer_gets_no_events() -> None:
    # A pure signal-consumer must not be offered the raw event.
    sig = _SignalDetector()
    signals = fan_out([sig], _event(0))
    assert sig.seen == []      # no upstream signals existed to feed it
    assert signals == []


def test_reset_clears_state() -> None:
    det = _EventDetector()
    fan_out([det], _event(0))
    assert det.seen == 1
    det.reset()
    assert det.seen == 0
