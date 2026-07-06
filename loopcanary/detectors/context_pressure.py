"""context_pressure — the context window is filling up, maybe without progress.

Two failure shapes, one detector:

1. **Absolute** — context size crosses a hard ceiling. Long agent runs
   accumulate history until they approach the model's window and start
   truncating or erroring. Fires WARN on the rising edge of
   ``abs_threshold``.
2. **Ballooning without progress** — context grows fast while outputs stop
   changing. Over the last ``window`` steps, if the average token growth
   per step exceeds ``rate_threshold`` *and* the outputs show little
   novelty (``<= diversity_max`` distinct ``output_fingerprint`` values),
   the agent is stuffing context without getting anywhere. Fires WARN on
   the rising edge.

Handles missing token counts gracefully: if ``tokens_in_context`` is
``None``, the detector self-disables and emits a single INFO signal saying
so, then stays silent (it never crashes the host).

Defaults ``abs_threshold=100_000`` (near common context limits — set it to
roughly 0.8 × your model's window), ``rate_threshold=2000`` tokens/step
(sustained multi-thousand-token growth per step is a lot),
``window=10, diversity_max=2``.
"""

from __future__ import annotations

from collections import deque

from loopcanary.protocol import Severity, Signal
from loopcanary.schema import LoopEvent


class ContextPressure:
    """Detect absolute context-size limits and ballooning-without-progress."""

    name = "context_pressure"
    consumes = frozenset({"event"})

    def __init__(
        self,
        abs_threshold: int = 100_000,
        rate_threshold: float = 2000.0,
        window: int = 10,
        diversity_max: int = 2,
    ) -> None:
        if window < 2:
            raise ValueError("window must be >= 2 to measure a growth rate")
        self.abs_threshold = abs_threshold
        self.rate_threshold = rate_threshold
        self.window = window
        self.diversity_max = diversity_max
        # (step, tokens, output_fingerprint) for events that carry tokens.
        self._recent: deque[tuple[int, int, str]] = deque(maxlen=window)
        self._abs_fired = False
        self._rate_fired = False
        self._disabled = False
        self._disabled_announced = False

    def consume(self, item: LoopEvent | Signal) -> list[Signal]:
        if not isinstance(item, LoopEvent):
            return []

        if item.tokens_in_context is None:
            # Self-disable once, loudly but harmlessly.
            if self._disabled_announced:
                return []
            self._disabled = True
            self._disabled_announced = True
            return [
                Signal(
                    detector=self.name,
                    severity=Severity.INFO,
                    step=item.step,
                    pattern="disabled_no_tokens",
                    message="context_pressure disabled: events carry no token counts",
                    evidence={"reason": "tokens_in_context is None"},
                )
            ]
        if self._disabled:
            return []

        tokens = item.tokens_in_context
        self._recent.append((item.step, tokens, item.output_fingerprint))
        out: list[Signal] = []

        # 1. Absolute ceiling (rising edge).
        if tokens >= self.abs_threshold:
            if not self._abs_fired:
                self._abs_fired = True
                out.append(
                    Signal(
                        detector=self.name,
                        severity=Severity.WARN,
                        step=item.step,
                        pattern="context_over_threshold",
                        message=f"context {tokens} tokens >= threshold {self.abs_threshold}",
                        evidence={"tokens": tokens, "threshold": self.abs_threshold},
                    )
                )
        else:
            self._abs_fired = False  # re-arm if it drops back down

        # 2. Ballooning without progress (needs a full window).
        if len(self._recent) == self.window:
            first_step, first_tokens, _ = self._recent[0]
            span = item.step - first_step
            rate = (tokens - first_tokens) / span if span > 0 else 0.0
            distinct_outputs = len({f for (_, _, f) in self._recent})
            ballooning = rate >= self.rate_threshold and distinct_outputs <= self.diversity_max
            if ballooning and not self._rate_fired:
                self._rate_fired = True
                out.append(
                    Signal(
                        detector=self.name,
                        severity=Severity.WARN,
                        step=item.step,
                        pattern="context_ballooning_no_progress",
                        message=(
                            f"context growing ~{rate:.0f} tok/step with only "
                            f"{distinct_outputs} distinct output(s)"
                        ),
                        evidence={
                            "rate_tokens_per_step": round(rate, 1),
                            "rate_threshold": self.rate_threshold,
                            "distinct_outputs": distinct_outputs,
                            "window": self.window,
                        },
                    )
                )
            elif not ballooning:
                self._rate_fired = False

        return out

    def reset(self) -> None:
        self._recent.clear()
        self._abs_fired = False
        self._rate_fired = False
        self._disabled = False
        self._disabled_announced = False
