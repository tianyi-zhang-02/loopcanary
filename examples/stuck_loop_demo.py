"""stuck_loop_demo — watch loopcanary flag a stuck agent in 5 seconds.

A fake agent that "decides" to keep running the same failing command,
getting the same error back every time — the classic loop-of-death. We
wrap the loop in a Canary and print signals as they fire.

Run:  python examples/stuck_loop_demo.py

No external dependencies. Expect a repeated_action WARN then ALERT, and a
null_progress ALERT once the output stops changing.
"""

from __future__ import annotations

from loopcanary import Canary, Signal


def fake_agent_step(step: int) -> tuple[str, str]:
    """A broken agent: always retries the same command, always fails."""
    action = {"tool": "bash", "cmd": "python train.py --resume"}
    output = "FileNotFoundError: checkpoint.pt not found"
    # (A healthy agent would vary its action after the first failure.)
    return str(action), output


def main() -> None:
    def alarm(sig: Signal) -> None:
        print(f"  ⚠️  [{sig.severity.name}] {sig.detector}: {sig.message}")

    canary = Canary(on_signal=alarm)

    print("Running a deliberately stuck agent loop for 12 steps...\n")
    for step in range(12):
        action, output = fake_agent_step(step)
        signals = canary.observe_raw(action=action, output=output, action_type="tool:bash")
        marker = "  <- fired" if signals else ""
        print(f"step {step:2d}: retry train.py{marker}")

    print("\nEnd-of-run summary:")
    for detector, counts in canary.summary().items():
        print(f"  {detector}: {counts}")


if __name__ == "__main__":
    main()
