# loopcanary

**The pytest of agent-loop health.** A pip-installable, in-process Python
library that watches an agent loop from *inside* your process and emits
structured signals when the loop starts to degrade — the same action on
repeat, no new output, context ballooning without progress.

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Status: v0.1.0](https://img.shields.io/badge/status-v0.1.0-orange.svg)](SCOPE.md)

No backend. No dashboard. No LLM judge in the core. No network I/O. No data
leaves your process. The core is stdlib-only with zero runtime
dependencies, which means it runs in production **and** inside a training
rollout worker — where a per-trace LLM judge is cost-absurd but a
hash-based repeated-action check costs microseconds.

```bash
pip install loopcanary   # (once published; for now, pip install -e .)
```

## Quickstart

Wrap **any loop you drive in your own Python process** — a hand-rolled
`while` loop, an agent SDK loop, or an RL rollout worker — in about five
lines:

```python
from loopcanary import Canary

canary = Canary(on_signal=lambda s: print(f"[{s.severity.name}] {s.detector}: {s.message}"))

for step in agent_loop():
    for signal in canary.observe_raw(action=step.action, output=step.result, tokens=step.context_tokens):
        handle(signal)   # log it, break the loop, penalize the rollout — your call

for detector, counts in canary.summary().items():
    print(detector, counts)   # end-of-run digest
```

`observe_raw` fingerprints the action and output for you and auto-increments
the step counter. For mapping payloads that carry run-specific fields, pass
`action_volatile` or `output_volatile` so values like request IDs and
timestamps do not hide repeated behavior:

```python
canary.observe_raw(
    action={"tool": "bash", "cmd": "python train.py --resume", "request_id": rid},
    output={"error": "FileNotFoundError", "timestamp": now},
    action_volatile={"request_id"},
    output_volatile={"timestamp"},
)
```

If you already build event objects, feed them directly:

```python
from loopcanary import Canary, LoopEvent, fingerprint

canary = Canary()
event = LoopEvent(
    step=0,
    action_type="tool:bash",
    action_fingerprint=fingerprint({"cmd": "python train.py --resume"}),
    output_fingerprint=fingerprint("FileNotFoundError: checkpoint.pt not found"),
    tokens_in_context=5123,
)
signals = canary.observe(event)
```

One `Canary` per loop (or per rollout). It is **not thread-safe by
design** — locks would tax the per-event hot path, and the intended shape
is one instance per loop. Run many loops in parallel? Give each its own.

See [`examples/stuck_loop_demo.py`](examples/stuck_loop_demo.py) for a
runnable stuck-agent demo, and
[`examples/rollout_shape_demo.py`](examples/rollout_shape_demo.py) for the
in-RL-rollout usage shape.

## Why this exists

The tracing platforms (LangSmith, Langfuse, Phoenix) **record and display**
— they show you the loop in a waterfall *after* the fact, and you find the
problem by squinting at a UI or writing an LLM-judge eval. None of them is a
thing you `import` that runs the check *in your process, in your loop, right
now, for free, offline*. loopcanary is a library, not a platform — and that
is the whole point. The moment it grows a backend or a dashboard it
re-enters the platform tier and loses the one property that makes it useful
inside a training loop: it costs almost nothing and nothing leaves the box.

There is a longer reason, too. As agentic systems scale, oversight stops
being a human watching every step and becomes *instrumented
monitorability* — cheap always-on signals wired into the loop, with scarce
human and model attention spent only where those signals point. Attention
isn't removed, it's rationed. That is exactly the shape here: a deterministic
first layer scans every step at microsecond cost, and a more expensive
second layer (an LLM judge, a learned probe — third-party, not in this
package) is meant to fire only on the windows the cheap layer flags. The
cascade is that attention hierarchy in miniature: machine signal → optional
judge → human. v1 ships the cheap layer and the stable interface the
expensive layers plug into; it makes no claim about how well any of it
catches real failures — that is what the validation harness below is for.

## What it detects (v1.0)

All deterministic, all in-process — no model calls, no network:

| detector | fires when | default thresholds |
|---|---|---|
| `repeated_action` | the same action fingerprint recurs within a sliding window | WARN at `n=3`, ALERT at `2n`, `window=10` |
| `null_progress` | output fingerprints stop diversifying over a window | `window=8`, WARN when distinct ≤ `k=2`, ALERT when distinct = 1 |
| `context_pressure` | context crosses an absolute token budget, or balloons fast while output stays stuck | `abs_threshold=100_000`, `rate_threshold=2000`/step, `window=10`, `diversity_max=2` |

Signals carry a `severity` (`INFO` / `WARN` / `ALERT`), the `step`, a stable
`pattern` string, a human `message`, and an `evidence` dict. Detectors fire
on the **rising edge** (once per threshold crossing), not once per step, so
they don't spam. `context_pressure` self-disables with a single `INFO` if
events carry no token counts, rather than silently doing nothing.

### Detectors are layered

Detectors are a `runtime_checkable` `Protocol` with a `consumes` set that
declares whether a detector reads raw events, other detectors' signals, or
both. That makes the layering explicit: the deterministic detectors consume
`event`s and run always-on at near-zero cost; a second-stage detector (an
LLM judge, a learned probe) can declare `consumes={"signal"}` and fire only
on the cheap layer's flagged windows — the standard cheap-filter →
expensive-confirm shape.

**v1 ships only the deterministic layer plus the stable cascade interface.**
The judge itself is deliberately *not* in this package — it would be the one
thing that sends data out of your process, and it belongs to whoever needs
it, as a third-party detector. Bring your own in ~20 lines by implementing
the `Detector` protocol.

## Validation

Detector quality is measured, not asserted.
[`scripts/validate_trace.py`](scripts/validate_trace.py) scores the
detectors against a labeled trajectory dataset (e.g. Patronus's TRACE),
reporting per-detector and pooled precision / recall / F1 under two
detection definitions (strict = ALERT-only, lenient = WARN-or-above).

```bash
python scripts/validate_trace.py --dataset path/to/trace.jsonl --detection lenient
```

| dataset | detection | detector | precision | recall | F1 |
|---|---|---|---|---|---|
| — | — | — | _[to be filled by a validation run]_ | _[…]_ | _[…]_ |

These numbers are intentionally blank. They get filled by running the script
above on a real dataset — never by hand. Until then, treat the detector list
as a design, not a benchmarked result.

## Adapters

loopcanary reads canonical `LoopEvent`s. Adapters map foreign traces onto
them; foreign-format assumptions live only in the adapter, never in the
detectors.

- **Claude Code** — `loopcanary.adapters.claude_code.ClaudeCodeSession`
  parses a Claude Code JSONL transcript into events (one per tool call,
  paired with its result), tolerating malformed lines and unknown record
  types. It also has a CLI:

  ```bash
  python -m loopcanary.adapters.claude_code --watch <transcript.jsonl>
  ```

  Caveat: transcript mode detects **as-written** (near-real-time), not
  pre-step. The in-process `Canary` is where pre-step callbacks are real.

Wanted adapters (Codex, LangGraph, AutoGen, OpenTelemetry) are tracked in
[`docs/BACKLOG.md`](docs/BACKLOG.md).

## Limitations (honest)

- **Deterministic only.** These detectors catch *structural* degeneration —
  repetition, stalled output, context blowup. They do not judge semantics: a
  loop that "makes progress" toward a wrong goal looks healthy to them. That
  is what the (out-of-core) judge layer is for.
- **Fingerprint-based.** Detection is only as good as your fingerprints. If
  two meaningfully-different actions hash the same, or a nominally-identical
  action carries a volatile field (a timestamp, a UUID), tune what you feed
  in — `fingerprint(..., volatile={...})` strips caller-marked keys.
- **No effectiveness claim yet.** The README ships with blank validation
  numbers on purpose (see above).
- **Not thread-safe.** One `Canary` per loop. By design.

## Non-goals (v1, frozen)

No dashboard, UI, server, or network I/O. No LLM-judge detector in the core
(the protocol supports one as a third-party plugin; we don't ship it). No
entropy/logprob detectors (the schema carries the field; no detector
consumes it yet). No auto-intervention or loop-breaking (loopcanary
*detects*; what you do is yours). No aggregate "health score." The full
in/out line is in [`SCOPE.md`](SCOPE.md); deferred ideas are in
[`docs/BACKLOG.md`](docs/BACKLOG.md).

The scope freeze is the design, not a lack of ambition: staying a library is
what keeps loopcanary cheap enough to run where platforms can't.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The most useful contributions right
now are **new adapters** and **new detectors** implementing the `Detector`
protocol — start from the wanted lists in
[`docs/BACKLOG.md`](docs/BACKLOG.md). API-shape feedback on the `Canary`
surface, the `Detector` protocol, and the `LoopEvent` schema is especially
welcome before the interface locks under semver at the v1.0 tag.

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
