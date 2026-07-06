"""null_progress — steps advance but nothing new comes back.

Complements ``repeated_action``: the agent might vary its actions slightly
yet still make no observable progress — the *outputs* stop changing. If the
set of distinct ``output_fingerprint`` values over the last ``window`` steps
collapses to ``k`` or fewer while the step counter keeps climbing, the loop
is spinning.

Fires WARN when distinct outputs over the window ``<= k``; escalates to
ALERT when everything is identical (distinct == 1 — total stall). Fires on
the rising edge (once when it becomes stuck), and re-arms once the loop
recovers (distinct rises back above ``k``).

Defaults ``window=8, k=2``: over eight steps, seeing only one or two
distinct results means the agent is treading water. Eight is long enough to
avoid flagging a brief plateau; ``k=2`` tolerates a benign A/B alternation
while catching genuine stalls.
"""

from __future__ import annotations

from collections import Counter, deque

from loopcanary.protocol import Severity, Signal
from loopcanary.schema import LoopEvent


class NullProgress:
    """Detect a collapse in output novelty over a sliding window."""

    name = "null_progress"
    consumes = frozenset({"event"})

    def __init__(self, window: int = 8, k: int = 2) -> None:
        if window < 1 or k < 1:
            raise ValueError("window and k must be >= 1")
        self.window = window
        self.k = k
        self._recent: deque[tuple[int, str]] = deque(maxlen=window)
        self._fired = False  # rising-edge latch

    def consume(self, item: LoopEvent | Signal) -> list[Signal]:
        if not isinstance(item, LoopEvent):
            return []
        self._recent.append((item.step, item.output_fingerprint))

        # Need a full window before judging "no progress".
        if len(self._recent) < self.window:
            return []

        counts = Counter(f for (_, f) in self._recent)
        distinct = len(counts)

        if distinct > self.k:
            # Progress resumed — re-arm so we can fire again if it stalls.
            self._fired = False
            return []

        if self._fired:
            return []
        self._fired = True

        dominant, dom_count = counts.most_common(1)[0]
        severity = Severity.ALERT if distinct == 1 else Severity.WARN
        return [
            Signal(
                detector=self.name,
                severity=severity,
                step=item.step,
                pattern="no_output_novelty",
                message=(
                    f"only {distinct} distinct output(s) in the last "
                    f"{self.window} steps"
                ),
                evidence={
                    "window": self.window,
                    "distinct": distinct,
                    "dominant_fingerprint": dominant,
                    "dominant_count": dom_count,
                },
            )
        ]

    def reset(self) -> None:
        self._recent.clear()
        self._fired = False
