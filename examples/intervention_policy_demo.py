"""Show one practical policy for acting on loopcanary signals.

loopcanary detects; your host loop decides what to do. This example keeps the
core policy simple:

* INFO: record diagnostic metadata.
* WARN: log and continue.
* ALERT: stop the loop and return a penalty-shaped result.

Run from a checkout:

    python examples/intervention_policy_demo.py
"""

from __future__ import annotations

from dataclasses import dataclass

from loopcanary import Canary, Severity, Signal


@dataclass(frozen=True)
class Step:
    action: dict[str, object]
    output: dict[str, object]
    tokens: int


def stuck_agent_loop() -> list[Step]:
    return [
        Step(
            action={
                "tool": "bash",
                "cmd": "python train.py --resume",
                "request_id": f"req-{step_index}",
            },
            output={
                "error": "FileNotFoundError: checkpoint.pt",
                "timestamp": f"2026-07-06T00:00:{step_index:02d}Z",
            },
            tokens=2_000 + step_index * 200,
        )
        for step_index in range(12)
    ]


def policy(signals: list[Signal]) -> str:
    if any(signal.severity is Severity.ALERT for signal in signals):
        return "stop"
    if any(signal.severity is Severity.WARN for signal in signals):
        return "warn"
    return "continue"


def main() -> int:
    canary = Canary()

    for step_index, step in enumerate(stuck_agent_loop()):
        signals = canary.observe_raw(
            action=step.action,
            output=step.output,
            tokens=step.tokens,
            action_type="tool:bash",
            action_volatile={"request_id"},
            output_volatile={"timestamp"},
        )
        decision = policy(signals)
        print(f"step={step_index:02d} decision={decision}")
        for signal in signals:
            print(f"  [{signal.severity.name}] {signal.detector}: {signal.message}")
        if decision == "stop":
            print("intervention: stop loop, mark rollout as degenerate, apply penalty=-1.0")
            break

    print("summary:", canary.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
