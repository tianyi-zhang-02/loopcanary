"""Boundary tests for the three deterministic detectors."""

from __future__ import annotations

from loopcanary.detectors import ContextPressure, NullProgress, RepeatedAction
from loopcanary.protocol import Severity
from loopcanary.schema import LoopEvent, fingerprint


def ev(step: int, action: str = "a", output: str | None = None, tokens: int | None = None) -> LoopEvent:
    return LoopEvent(
        step=step,
        action_type="tool:t",
        action_fingerprint=fingerprint(action),
        output_fingerprint=fingerprint(output if output is not None else f"out{step}"),
        tokens_in_context=tokens,
    )


def feed(det, events):  # type: ignore[no-untyped-def]
    signals = []
    for e in events:
        signals.extend(det.consume(e))
    return signals


# ---------------------------------------------------------------------------
# repeated_action
# ---------------------------------------------------------------------------


def test_repeated_action_below_threshold_no_fire() -> None:
    det = RepeatedAction(n=3, window=10)
    sigs = feed(det, [ev(i, action="same") for i in range(2)])  # 2 < 3
    assert sigs == []


def test_repeated_action_warns_at_n() -> None:
    det = RepeatedAction(n=3, window=10)
    sigs = feed(det, [ev(i, action="same") for i in range(3)])  # 3rd triggers
    assert len(sigs) == 1
    assert sigs[0].severity is Severity.WARN
    assert sigs[0].evidence["count"] == 3


def test_repeated_action_alerts_at_2n_and_fires_once_per_threshold() -> None:
    det = RepeatedAction(n=3, window=100)
    sigs = feed(det, [ev(i, action="same") for i in range(6)])  # 6 == 2n
    sevs = [s.severity for s in sigs]
    # exactly one WARN (at 3) and one ALERT (at 6) — not one per step.
    assert sevs.count(Severity.WARN) == 1
    assert sevs.count(Severity.ALERT) == 1
    assert len(sigs) == 2


def test_repeated_action_distinct_actions_no_fire() -> None:
    det = RepeatedAction(n=3, window=10)
    sigs = feed(det, [ev(i, action=f"act{i}") for i in range(10)])
    assert sigs == []


def test_repeated_action_window_evicts_old_repeats() -> None:
    det = RepeatedAction(n=3, window=3)
    # Same action at steps 0, 5, 10 — never 3 within any 3-step window.
    sigs = feed(det, [ev(0, "s"), ev(5, "s"), ev(10, "s")])
    assert sigs == []


def test_repeated_action_config_and_reset() -> None:
    det = RepeatedAction(n=2, window=5)
    assert feed(det, [ev(0, "s"), ev(1, "s")])[0].severity is Severity.WARN
    det.reset()
    assert len(det._recent) == 0
    # after reset, the counter starts over
    assert feed(det, [ev(0, "s")]) == []


# ---------------------------------------------------------------------------
# null_progress
# ---------------------------------------------------------------------------


def test_null_progress_partial_window_no_fire() -> None:
    det = NullProgress(window=8, k=2)
    sigs = feed(det, [ev(i, output="same") for i in range(7)])  # < window
    assert sigs == []


def test_null_progress_warns_when_diversity_low() -> None:
    det = NullProgress(window=8, k=2)
    # 8 steps, outputs alternate between 2 values -> distinct == 2 <= k.
    outs = ["A", "B"] * 4
    sigs = feed(det, [ev(i, output=outs[i]) for i in range(8)])
    assert len(sigs) == 1
    assert sigs[0].severity is Severity.WARN
    assert sigs[0].evidence["distinct"] == 2


def test_null_progress_alerts_when_totally_stuck() -> None:
    det = NullProgress(window=8, k=2)
    sigs = feed(det, [ev(i, output="same") for i in range(8)])
    assert sigs[0].severity is Severity.ALERT
    assert sigs[0].evidence["distinct"] == 1


def test_null_progress_diverse_outputs_no_fire() -> None:
    det = NullProgress(window=8, k=2)
    sigs = feed(det, [ev(i, output=f"o{i}") for i in range(20)])
    assert sigs == []


def test_null_progress_fires_once_then_rearms() -> None:
    det = NullProgress(window=4, k=1)
    # stuck for a while (fires once), then recovers, then stuck again (fires again)
    events = (
        [ev(i, output="X") for i in range(4)]          # fire #1 at step 3
        + [ev(i, output=f"n{i}") for i in range(4, 8)]  # recover, re-arm
        + [ev(i, output="Y") for i in range(8, 12)]     # fire #2
    )
    sigs = feed(det, events)
    assert len(sigs) == 2


def test_null_progress_reset() -> None:
    det = NullProgress(window=4, k=1)
    feed(det, [ev(i, output="X") for i in range(4)])
    det.reset()
    assert list(det._recent) == []
    assert det._fired is False


# ---------------------------------------------------------------------------
# context_pressure
# ---------------------------------------------------------------------------


def test_context_pressure_none_tokens_announces_once() -> None:
    det = ContextPressure()
    sigs = feed(det, [ev(i, tokens=None) for i in range(5)])
    assert len(sigs) == 1
    assert sigs[0].severity is Severity.INFO
    assert sigs[0].pattern == "disabled_no_tokens"


def test_context_pressure_recovers_after_initial_tokenless_events() -> None:
    det = ContextPressure(abs_threshold=1000, window=2)
    sigs = feed(
        det,
        [
            ev(0, tokens=None),
            ev(1, tokens=None),
            ev(2, tokens=500),
            ev(3, tokens=1200),
        ],
    )
    assert any(s.pattern == "disabled_no_tokens" for s in sigs)
    threshold = [s for s in sigs if s.pattern == "context_over_threshold"]
    assert len(threshold) == 1
    assert threshold[0].evidence["tokens"] == 1200


def test_context_pressure_absolute_threshold_fires_once() -> None:
    det = ContextPressure(abs_threshold=1000, window=2)
    sigs = feed(det, [ev(0, tokens=500), ev(1, tokens=1200), ev(2, tokens=1300)])
    warns = [s for s in sigs if s.pattern == "context_over_threshold"]
    assert len(warns) == 1
    assert warns[0].severity is Severity.WARN
    assert warns[0].evidence["tokens"] == 1200


def test_context_pressure_below_threshold_no_fire() -> None:
    det = ContextPressure(abs_threshold=100_000, rate_threshold=1e12, window=3)
    sigs = feed(det, [ev(i, tokens=100 * i) for i in range(10)])
    assert sigs == []


def test_context_pressure_ballooning_without_progress_fires() -> None:
    # Fast token growth (3000/step) + identical outputs -> ballooning.
    det = ContextPressure(abs_threshold=10_000_000, rate_threshold=2000, window=4, diversity_max=2)
    sigs = feed(det, [ev(i, output="stuck", tokens=3000 * (i + 1)) for i in range(4)])
    balloon = [s for s in sigs if s.pattern == "context_ballooning_no_progress"]
    assert len(balloon) == 1
    assert balloon[0].severity is Severity.WARN


def test_context_pressure_growth_with_progress_no_rate_fire() -> None:
    # Same fast growth but with diverse outputs -> not "without progress".
    det = ContextPressure(abs_threshold=10_000_000, rate_threshold=2000, window=4, diversity_max=2)
    sigs = feed(det, [ev(i, output=f"o{i}", tokens=3000 * (i + 1)) for i in range(4)])
    balloon = [s for s in sigs if s.pattern == "context_ballooning_no_progress"]
    assert balloon == []


def test_context_pressure_reset() -> None:
    det = ContextPressure(abs_threshold=1000, window=2)
    feed(det, [ev(0, tokens=1200)])
    det.reset()
    assert det._abs_fired is False
    assert list(det._recent) == []
