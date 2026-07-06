"""repeated_action — the agent keeps taking the same action.

The canonical loop-of-death: an agent calls the same tool with the same
arguments over and over (retrying a failing command, re-reading the same
file, looping on a broken plan) and burns budget without progressing.

Fires when the same ``action_fingerprint`` appears ``n`` times within a
sliding window of ``window`` steps. Severity escalates: WARN the first time
the count reaches ``n``, ALERT if it reaches ``2*n``. It fires on the
*rising edge* of each threshold, not every step past it, so a stuck loop
produces two signals (WARN then ALERT), not a hundred.

Defaults ``n=3, window=10``: three identical actions inside ten steps is a
strong loop signal with very few false positives — legitimate retries are
usually 1–2, and a genuinely stuck agent blows well past three. Ten steps
keeps the window short enough that unrelated repeats far apart don't
accumulate.
"""

from __future__ import annotations

from collections import deque

from loopcanary.protocol import Severity, Signal
from loopcanary.schema import LoopEvent


class RepeatedAction:
    """Detect the same action repeating within a sliding step window."""

    name = "repeated_action"
    consumes = frozenset({"event"})

    def __init__(self, n: int = 3, window: int = 10) -> None:
        if n < 1 or window < 1:
            raise ValueError("n and window must be >= 1")
        self.n = n
        self.window = window
        # (step, action_fingerprint) for the last `window` steps.
        self._recent: deque[tuple[int, str]] = deque()
        # Fingerprints we have already WARNed / ALERTed on, so we fire once
        # per threshold crossing rather than every subsequent step.
        self._warned: set[str] = set()
        self._alerted: set[str] = set()

    def consume(self, item: LoopEvent | Signal) -> list[Signal]:
        if not isinstance(item, LoopEvent):
            return []
        fp = item.action_fingerprint
        self._recent.append((item.step, fp))
        # Evict anything older than the window (by step distance).
        while self._recent and item.step - self._recent[0][0] >= self.window:
            self._recent.popleft()

        matching = [s for (s, f) in self._recent if f == fp]
        count = len(matching)

        if count >= 2 * self.n and fp not in self._alerted:
            self._alerted.add(fp)
            return [self._signal(item.step, fp, count, matching, Severity.ALERT)]
        if count >= self.n and fp not in self._warned:
            self._warned.add(fp)
            return [self._signal(item.step, fp, count, matching, Severity.WARN)]
        return []

    def _signal(
        self, step: int, fp: str, count: int, steps: list[int], severity: Severity
    ) -> Signal:
        return Signal(
            detector=self.name,
            severity=severity,
            step=step,
            pattern="same_action_repeated",
            message=(
                f"action {fp} repeated {count}x within {self.window} steps"
            ),
            evidence={
                "action_fingerprint": fp,
                "count": count,
                "window": self.window,
                "steps": list(steps),
            },
        )

    def reset(self) -> None:
        self._recent.clear()
        self._warned.clear()
        self._alerted.clear()
