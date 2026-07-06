"""Tests for the Canary in-process API."""

from __future__ import annotations

from loopcanary import Canary, LoopEvent, Severity, Signal, fingerprint


def test_observe_raw_auto_increments_step() -> None:
    canary = Canary()
    # Feed distinct actions so nothing fires; check steps advance 0,1,2.
    steps = []

    class _Probe:
        name = "probe"
        consumes = frozenset({"event"})

        def consume(self, item):  # type: ignore[no-untyped-def]
            steps.append(item.step)
            return []

        def reset(self) -> None:
            steps.clear()

    canary = Canary(detectors=[_Probe()])
    canary.observe_raw(action="a", output="x")
    canary.observe_raw(action="b", output="y")
    canary.observe_raw(action="c", output="z")
    assert steps == [0, 1, 2]


def test_observe_raw_fingerprints_and_fires_repeated_action() -> None:
    canary = Canary()
    fired = []
    for _ in range(3):
        fired.extend(canary.observe_raw(action="same", output="err", action_type="tool:bash"))
    assert any(s.detector == "repeated_action" and s.severity is Severity.WARN for s in fired)


def test_on_signal_callback_invoked() -> None:
    received: list[Signal] = []
    canary = Canary(on_signal=received.append)
    for _ in range(3):
        canary.observe_raw(action="same", output="err")
    assert any(s.detector == "repeated_action" for s in received)


def test_summary_shape() -> None:
    canary = Canary()
    for _ in range(6):
        canary.observe_raw(action="same", output="err")
    summ = canary.summary()
    assert "repeated_action" in summ
    ra = summ["repeated_action"]
    assert set(ra) == {"INFO", "WARN", "ALERT", "total"}
    assert ra["WARN"] == 1
    assert ra["ALERT"] == 1
    assert ra["total"] == 2


def test_observe_accepts_prebuilt_event() -> None:
    canary = Canary()
    e = LoopEvent(
        step=0,
        action_type="message",
        action_fingerprint=fingerprint("hi"),
        output_fingerprint=fingerprint("ok"),
        tokens_in_context=100,  # avoid the context_pressure "no tokens" INFO
    )
    assert canary.observe(e) == []  # single benign event, nothing fires


def test_context_manager_resets_on_enter() -> None:
    canary = Canary()
    for _ in range(3):
        canary.observe_raw(action="same", output="err")
    assert canary.summary()["repeated_action"]["total"] >= 1
    with canary as c:
        # reset on enter -> clean slate
        assert c.summary() == {}


def test_reset_clears_step_and_counts() -> None:
    canary = Canary()
    for _ in range(3):
        canary.observe_raw(action="same", output="err")
    canary.reset()
    assert canary.summary() == {}
    # step restarts at 0 after reset
    steps = []

    class _P:
        name = "p"
        consumes = frozenset({"event"})

        def consume(self, item):  # type: ignore[no-untyped-def]
            steps.append(item.step)
            return []

        def reset(self) -> None:
            pass

    c2 = Canary(detectors=[_P()])
    c2.observe_raw(action="a", output="b")
    assert steps == [0]


def test_custom_detectors_and_thresholds() -> None:
    from loopcanary.detectors import RepeatedAction

    canary = Canary(detectors=[RepeatedAction(n=2, window=5)])
    fired = []
    for _ in range(2):
        fired.extend(canary.observe_raw(action="same", output="e"))
    assert any(s.severity is Severity.WARN for s in fired)
