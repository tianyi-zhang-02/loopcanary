# loopcanary

**The pytest of agent-loop health.** A pip-installable, in-process
Python library that catches your agent's loop going wrong —
reasoning loops, null progress, context pressure, cost run-away —
with cheap deterministic checks that run *inside* the loop.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Status: v1.0 in development](https://img.shields.io/badge/status-v1.0%20in%20development-orange.svg)](docs/pivot_v1_agentic.md)

No backend. No dashboard. No LLM judge. No data leaving your process.
It runs in production **and** inside a training rollout worker, where a
per-trace LLM judge is cost-absurd but a hash-based repeated-action
check is free.

> **Status: v1.0 in development.** This repo currently holds the
> data-model seed (`src/loopcanary/core/`). The `watch()` API below is
> the target design, specified in
> [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md) and
> [`docs/v1_scope.md`](docs/v1_scope.md) — not yet implemented. Star
> the repo to follow; API-shape feedback is wanted now, before the
> surface locks at v1.0.

## Why this exists

Everyone built Datadog for agents. Nobody built the pytest.

The tracing platforms (LangSmith, Langfuse, Phoenix, MLflow, SigNoz)
**record and display** — they show you the loop in a trace waterfall
*after* the fact, and you find it by squinting at the UI or writing an
LLM-judge eval. The detection products (Raindrop, Laminar) **do**
detect loops — but only as platform-attached, send-your-traces-out,
LLM-judge-or-paid services.

None of them are a library you `import` that runs the check *in your
process, in your loop, right now, for free*. That's the gap.

**"Why not just a Langfuse eval?"** Because loopcanary is zero-infra
and in-process: it works offline, in air-gapped environments, and
inside training loops — none of which a platform-attached LLM-judge
eval can do. If you already run Langfuse or Phoenix, loopcanary is
complementary, not a replacement: it emits events compatible with the
OpenTelemetry `gen_ai.*` conventions, so you can pipe its detections
straight into your existing traces.

## Quickstart (target API — v1.0)

```bash
pip install loopcanary
```

Wrap **any agent loop you run in your own Python process** in five
lines — the Claude Agent SDK, LangChain, LlamaIndex, a hand-rolled
`while` loop, or an RL rollout worker:

```python
import loopcanary as lc

with lc.watch(
    detectors=[
        lc.detectors.repeated_action(threshold=3),   # same tool+args N times
        lc.detectors.null_progress(window=5),         # no state change in K steps
        lc.detectors.context_pressure(warn_at=0.8),   # nearing the context window
        lc.detectors.cost_burn_rate(usd_per_min=0.50),
    ],
    on_alarm=lambda sig: print(f"⚠️  {sig.detector}: {sig.summary}"),  # live one-liner
) as run:
    result = agent.run(task)     # your loop, unchanged

run.report.render()              # post-run digest; run.trace(step=N) for the deep dive
```

Three integration shapes, all zero-config:

```python
# 1. context manager (above)  — recommended
# 2. wrap the model-API client — Anthropic, OpenAI, any provider
client = lc.instrument(Anthropic(), detectors=[...])   # every call is now watched
# 3. decorator
@lc.watch(detectors=[...])
def run_task(agent, task): ...
```

**The integration point is the model API, not the product.** You can't
wrap Claude Code or Codex — they're closed CLI *products*, separate
processes. But if you're calling the **same models via their API** —
the Anthropic or OpenAI client — inside a loop you drive, that's
in-process and loopcanary wraps it directly with `instrument(client)`.
Provider-agnostic: any model, any provider, as long as you own the
loop. (Monitoring the closed CLI products themselves needs a thin
hooks/OTel adapter — that's v1.1, see
[`docs/v1_scope.md`](docs/v1_scope.md).)

## What it detects (v1.0)

All deterministic, all zero-cost — no model calls, no network:

| detector | fires when |
|---|---|
| `repeated_action` | the same tool call with the same args repeats N times (hash-based) |
| `null_progress` | no observable state change over K steps |
| `context_pressure` | input tokens cross a fraction of the model's context window |
| `cost_burn_rate` | spend velocity exceeds a USD/min threshold |
| `compression_frequency` | context-compaction events fire above a rate |

Detectors are a `Protocol` — bring your own in ~20 lines.

### Detectors are layered

Detectors are layered: deterministic detectors run always-on at
near-zero cost; optional detectors (LLM-judge, learned probes) can
consume their signals for second-stage confirmation. **v1 ships the
deterministic layer; the cascade interface is stable.**

Concretely, the cheap layer scans every step and flags suspicious
windows; an opt-in second-stage detector fires *only on the flagged
windows* — "is this repeated action really stuck, or a legit retry?"
That's the standard cheap-filter → expensive-confirm shape: the judge
runs on the <5% of steps that were flagged, not a forward pass on
every step, and it filters the cheap layer's false positives while the
cheap layer keeps recall. It's a notch smarter than running two
detectors in parallel.

The default install is **pure deterministic** — that never changes;
it's what runs in a rollout worker. The judge is an opt-in extra
(`pip install loopcanary[judge]`): install it and you gain a detector;
don't and the core is a gram lighter. It is the one thing that sends
data out of your process, and it says so loudly. The judge itself, a
cascade reference implementation, and the precision-uplift numbers are
v1.1+/research — v1.0 ships only the interface that makes the cascade
buildable, not a refactor.

## Where it runs that platforms can't

The in-process, deterministic design is the only shape that works at
**training time**. Inside a GRPO rollout worker doing 16 rollouts per
prompt, a per-trace LLM judge is economically impossible — but a
hash-based repeated-action detector costs nothing and runs in the
worker. If you're doing RL on agents (NeMo-RL and friends),
loopcanary is the loop-health check you can actually afford to run on
every rollout.

## Progressive disclosure

One short alarm while the loop runs; escalate to full trace only when
it trips.

- **live** — a one-line alarm streamed via `on_alarm` (`⚠️ repeated_action: bash("ls") ×3 at steps 27–29`)
- **digest** — `run.report.render()`, a few lines: what fired, when, cost/context summary
- **trace** — `run.trace(step=27)`, the full event stream around a fire

## Honest competitive picture

- **Tracing platforms** (LangSmith, Langfuse, Phoenix, MLflow, SigNoz)
  — mature, converging on OTel GenAI semconv. They record; you detect
  by eye or by eval. **Substrate, not competitor** — pipe loopcanary's
  OTel-compatible events into them.
- **Detection products** (Raindrop, Laminar) — they *do* detect loops,
  but platform-attached, traces-leave-your-box, LLM-judge or paid
  ($65/mo+). loopcanary is the in-process, offline, free-at-training-time
  alternative.
- **Academic detectors** (TRACER et al.) — metrics in papers, not
  installable software.

**The moat is deliberately thin** and the scope freeze is the strategy:
the moment loopcanary grows a dashboard or a backend, it re-enters the
platform tier and gets annihilated. It stays a library. On purpose.
See [`docs/v1_scope.md`](docs/v1_scope.md) for the hard in/out line.

## Validation (roadmap, not a claim)

Detectors will be validated against a public labelled-failure
trajectory dataset (Patronus's TRACE, hundreds of labelled failure
runs). When that lands, this README will state **recall on public
data** — not "detects loops, trust me." Until then, treat the detector
list as a design, not a benchmarked result.

## What's here now

`src/loopcanary/core/` — the trajectory data model (`TrajectoryEvent`
variants, `SemanticVerdict`) the SDK is built on. Everything above is
target design in [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md)
+ [`docs/v1_scope.md`](docs/v1_scope.md).

The reward-hacking-monitor *robustness research* (the batch harness,
MALT experiments, the SaTML finding) lives in a **separate** repo,
[`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress).
Independent; neither repo imports the other.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). API-shape feedback on the
`watch()` signature, the `Detector` protocol, and the event schema is
the most useful thing you can give right now — the surface locks under
semver at the v1.0 tag.

## License

MIT — see [`LICENSE`](LICENSE).
