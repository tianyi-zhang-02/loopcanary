# Project State

*Last updated: 2026-07-06.*

## Identity

`loopcanary` is an open-source, stdlib-only Python library for in-process
agent-loop health detection. It watches loop steps through canonical
`LoopEvent`s and emits structured `Signal`s when cheap deterministic checks
see likely degradation: repeated actions, stalled outputs, or context
pressure.

It is a tool, not a hosted observability platform and not a benchmark claim.
The core does no network I/O, makes no model calls, and has no runtime
dependencies.

## Current Phase

`v0.1.0` is implemented on `main` as the first usable SDK release candidate:

- `Canary.observe()` and `Canary.observe_raw()` are the primary in-process API.
- `LoopEvent`, `Signal`, `Severity`, and the `Detector` protocol define the
  extension surface.
- Three deterministic detectors ship by default: `repeated_action`,
  `null_progress`, and `context_pressure`.
- The Claude Code JSONL adapter can inspect existing or live transcript files.
- `scripts/validate_trace.py` evaluates detectors against labeled JSONL trace
  datasets, but no real benchmark numbers are claimed yet.

## Active Work

- Harden the `v0.1.0` API based on local review and smoke testing.
- Keep documentation aligned with the implemented API before publishing.
- Validate on a real labeled trace dataset before filling README metric tables.

## Known Limits

- Deterministic signals catch structural degeneration, not semantic wrongness.
- The Claude Code adapter is transcript-based and emits events after matching
  tool results, so it is near-real-time/retrospective rather than pre-step.
- One `Canary` instance is intended per loop or rollout; it is not thread-safe.
- No dashboard, backend, cross-run service, or bundled LLM judge is in scope.

## Sibling Repo

[`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress) remains the
separate research harness for CoT-monitor robustness work. `loopcanary` should
stay focused on the SDK/tooling surface and should not import research harness
code.

## Useful Entry Points

- `README.md` — user-facing overview and quickstart.
- `loopcanary/api.py` — `Canary` in-process API.
- `loopcanary/schema.py` — canonical event schema and fingerprinting.
- `loopcanary/protocol.py` — detector protocol and signal fan-out.
- `loopcanary/detectors/` — shipped deterministic detectors.
- `loopcanary/adapters/claude_code.py` — Claude Code transcript adapter.
- `scripts/validate_trace.py` — labeled-trace validation harness.
