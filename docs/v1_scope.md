# loopcanary v1.0 — the in/out list

*The scope freeze is the competitive strategy, not just discipline.*
loopcanary survives in exactly one position: **a pip-installable,
in-process library — not a platform.** Everything below enforces that.
The moment an OUT item creeps IN, loopcanary re-enters the tracing-
platform tier (LangSmith / Langfuse / Phoenix / MLflow / SigNoz) and
gets annihilated. Ship the IN list, freeze the OUT list.

This is the weekend build target. If a task isn't on the IN list, it
doesn't go in v1.0.

## IN — v1.0 (build these, stop when done)

**Packaging**
- `pip install loopcanary`, in-process, zero required deps beyond
  `pydantic`. `rich` optional (terminal render only).
- Python 3.11+. Works offline, air-gapped, and inside training rollouts.

**Core API**
- `lc.watch(detectors=[...], on_alarm=...)` context manager.
- `lc.instrument(callable, detectors=[...])` — wrap any callable
  (covers LangChain, custom loops, Claude Agent SDK).
- `@lc.watch(...)` decorator.
- `Detector` protocol — cheap, called per event. Users bring their own
  in ~20 lines.
- **The cascade interface (the one thing added for layering):** a
  detector can consume the event stream **or** the signals emitted by
  upstream detectors — `check(events_so_far, signals_so_far) -> Signal
  | None`. This ten-line interface decision is what makes a
  cheap-filter → expensive-confirm cascade *buildable* rather than a
  refactor: a second-stage detector keys off first-stage signals and
  fires only on flagged windows. v1.0 ships **only this interface** —
  not the judge, not a cascade reference implementation, not
  precision-uplift numbers (those are v1.1+/research).

**Detectors (all deterministic, zero model calls, zero network)**
- `repeated_action(threshold)` — hash of (tool, args) repeats N times.
- `null_progress(window)` — no observable state change over K steps.
- `context_pressure(warn_at)` — input tokens cross a window fraction.
- `cost_burn_rate(usd_per_min)` — spend velocity threshold.
- `compression_frequency(max_per_hour)` — compaction-event rate.

**Output — progressive disclosure, terminal + files only**
- Live one-line alarm via `on_alarm` callback (stream to stderr /
  Slack / logger — the user's sink, not ours).
- `run.report.render()` — a few-line digest (Rich table in terminal).
- `run.trace(step=N)` — full event window on demand.
- Per-run JSON export.

**Interop (the two cheap credibility moves)**
- Event schema **compatible with OpenTelemetry `gen_ai.*`
  conventions**, so Tier-1 platforms become distribution, not
  competition (a Langfuse/Phoenix user pipes loopcanary events into
  their traces).
- A **validation harness** against a public labelled-failure dataset
  (Patronus TRACE) that prints **recall per detector** — so the README
  claims a number, not "trust me."

**Docs**
- Honest README with the "library not platform" line and the
  "why not a Langfuse eval?" answer (done).
- One runnable `examples/` script per integration shape (Claude Agent
  SDK, LangChain, a hand-rolled loop). CLI agents (Claude Code / Codex)
  are v1.1 adapters, not v1.0 examples.
- `CONTRIBUTING` oriented to API-shape feedback pre-freeze.

**Ship criterion:** a stranger installs it, wraps a loop in five lines,
sees a real detection, on a fresh machine, in under ten minutes.
**Done is a git tag (`v1.0.0`).**

## OUT — v1.0 (freeze; each one is a competitive death if it creeps in)

- **No hosted backend, dashboard, or web UI.** This is the line that
  matters most. A dashboard = re-entering the platform tier = death.
  Terminal render + JSON only.
- **No LLM-judge in the default install.** The identity is
  deterministic/cheap/local — layer one, always-on, what runs in a
  rollout worker. The judge is the **opt-in second layer**
  (`pip install loopcanary[judge]`), consuming layer-one signals for
  cheap-filter → expensive-confirm. v1.0 ships the *cascade interface*
  that makes this buildable, but **not** the judge itself, a reference
  cascade, or precision numbers — those are v1.1+/research. When the
  judge does ship it stays off by default and is the one thing that
  sends data out of the process, flagged loudly.
- **No data leaving the process by default.** Zero egress is a
  load-bearing property (it's why training-time works). The only
  exception is opt-in detectors the user explicitly turns on.
- **No persistence-as-a-service, no accounts, no team/collab.**
- **No LangChain-native integration in v1.0.** The generic
  `instrument(callable)` adapter covers LangChain users; a native
  integration is v1.1, demand-driven.
- **No semantic transformations, no reward-hacking research, no AUROC.**
  That is the `monitorstress` repo's job, not this one. loopcanary owes
  the paper nothing.
- **No memory-event / compression *analysis* engine in v1.0.** v1.0
  *surfaces* compaction events (`compression_frequency`); correlating
  compression with downstream degradation is v2.

## v1.1+ (parking lot — not now, not a design constraint)

- **CLI-agent adapters** (Claude Code / Codex) — thin adapters that
  consume the CLI's hooks / OpenTelemetry export / session logs and run
  the deterministic detectors alongside the process. Out-of-process by
  nature; per-tool maintenance; demand-driven.
- Native LangChain / LlamaIndex integrations.
- **The judge, matured** — `loopcanary[judge]` opt-in second layer, a
  cascade reference implementation, and the "how much precision the
  judge adds over the cheap layer" numbers (research/paper territory).
- Compression↔degradation correlation analysis.
- More deterministic detectors as public-dataset recall reveals gaps.

## v2.0 (only if v1.0 earns users)

- Local TUI for live streaming visualisation (still no hosted backend).
- Multi-run comparison.

## The one-sentence test

Before adding anything to v1.0, ask: *does this keep loopcanary a
library a developer imports, or does it push it toward a platform a
company logs into?* If the latter, it's OUT.
