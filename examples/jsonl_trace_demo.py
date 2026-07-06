"""Run loopcanary over a generic JSONL trace.

This demo writes a tiny trace to a temporary JSONL file, reads it through the
`JsonlTrace` adapter, and feeds the resulting LoopEvents into Canary.

Run from a checkout:

    python examples/jsonl_trace_demo.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from loopcanary import Canary
from loopcanary.adapters.jsonl_trace import JsonlTrace


def write_demo_trace(path: Path) -> None:
    rows = [
        {
            "step": step,
            "action_type": "handoff",
            "action": {
                "instruction": "Ask Codex to inspect the same failing test",
                "request_id": f"req-{step}",
            },
            "output": {"summary": "same failing assertion", "timestamp": f"t{step}"},
            "tokens_in_context": 1_000 + step * 250,
            "metadata": {"session_id": "demo-claude-codex", "actor": "claude"},
        }
        for step in range(3)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "handoff-trace.jsonl"
        write_demo_trace(trace_path)

        canary = Canary()
        for event in JsonlTrace(
            trace_path,
            action_volatile={"request_id"},
            output_volatile={"timestamp"},
        ).events():
            for signal in canary.observe(event):
                print(f"[{signal.severity.name}] {signal.detector}: {signal.message}")

        print("summary:", canary.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
