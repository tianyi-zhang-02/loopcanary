# loopcanary

**Diagnose when your agent's loop is degrading, its context is compressing, and its cost is running away.**

[![CI](https://img.shields.io/github/actions/workflow/status/tianyi-zhang-02/loopcanary/ci.yml?branch=main&label=ci)](https://github.com/tianyi-zhang-02/loopcanary/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Status: v1.0 in development](https://img.shields.io/badge/status-v1.0%20in%20development-orange.svg)](docs/pivot_v1_agentic.md)

`loopcanary` is an open-source Python library for **agent-loop
observability**. It watches an agent's execution as it happens and
diagnoses when its behaviour is going off-rails — the same tool call
firing over and over, silent context compression, memory writes that
never get recalled, cost run-away, or a safety monitor raising an
alarm. It emits a per-run timeline you can inspect after the fact
or stream live during execution.

This is not another generic tracer. LangSmith, Weave, Arize Phoenix,
and Braintrust already cover event capture and cost dashboards.
`loopcanary` covers the two things they underserve today:
**degradation diagnosis** (structured detectors that name the failure
mode, not just record it) and **compression / memory event surfacing**
(Claude's auto-compact and similar behaviours made visible and
correlated with downstream outcomes).

## Status

**v1.0 SDK in development.** The pivot from a batch stress-test CLI
to a streaming SDK was proposed and accepted 2026-06-08. See
[`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md) for the full
plan — scope, roadmap, competition, differentiation, risks, and the
four-commit implementation sequence.

**This repository currently contains the data-model seed** the SDK is
built on — `TrajectoryEvent` and `SemanticVerdict` in
[`src/loopcanary/core/`](src/loopcanary/core/) — plus the v1.0 plan.
The `watch()` / detector surface is not yet implemented.

**The batch experiments moved out.** The pre-pivot batch harness
(MALT ingestion, structural transformations, the METR reward-hacking
monitor, the AUROC report card) and the SaTML research finding now
live in a separate repository —
[`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress) —
which is independent of this one (neither imports the other). If you
came here for the reward-hacking-monitor robustness experiments,
that's the repo you want.

If you want the v1.0 SDK: not yet available. Watch the repository or
the changelog.

## What v1.0 will detect

The initial detector set:

| Detector | Purpose | Runs |
|---|---|---|
| `repeated_action` | Same tool call with same args firing N times in a row | Zero cost |
| `context_pressure` | Input tokens above a fraction of the model's context window | Zero cost |
| `cost_burn_rate` | Spend velocity above USD-per-minute threshold | Zero cost |
| `null_progress` | No observable state change over K steps | Zero cost |
| `compression_frequency` | Context compression events firing above rate threshold | Zero cost |
| `metr_safety` | METR's published reward-hacking monitor prompt, run periodically | LLM call |

Detectors are a `Protocol`. Users register their own with ~20 lines
of Python.

## What v1.0 will look like

The **v1.0 target API** — designed, not implemented yet. Do not
treat this as working code. Source of truth:
[`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md#v10-scope--tier-1-concrete-in-scope).

```python
import loopcanary as ms

with ms.watch(
    agent_id="research-assistant",
    detectors=[
        ms.detectors.repeated_action(threshold=3),
        ms.detectors.context_pressure(warn_at=0.8),
        ms.detectors.cost_burn_rate(usd_per_min_max=0.50),
        ms.detectors.metr_safety(model="haiku"),
        ms.detectors.null_progress(window_steps=5),
    ],
    output="./run.json",
) as run:
    result = my_agent.run(task)

run.report.render()  # Rich timeline in the terminal
```

Two additional integration modes are in the plan: Anthropic SDK
instrumentation (`ms.instrument(client)`) and a function decorator
(`@ms.watch(...)`).

## Roadmap

- **v0.1** *(shipped)* — batch CLI, stress-tests a monitor over saved
  MALT trajectories. Historical shape; remains runnable but not the
  primary interface.
- **v1.0** *(in development)* — Python SDK. `pip install loopcanary`;
  `import loopcanary as ms`; `with ms.watch(...) as run:`.
  Zero-config default, working output in under 10 minutes on a fresh
  machine. Ships with Claude Agent SDK integration + a generic
  wrap-any-callable API so LangChain users aren't locked out. Initial
  detector set above, a timeline report renderer, per-run JSON export.
- **v1.1** *(after v1.0)* — native LangChain integration, more
  detectors, more example integrations.
- **v2.0** *(later)* — local TUI/web dashboard for live streaming
  visualisation and multi-run comparison.

Explicit non-goals: no hosted dashboard, no team collaboration
features, no cross-run analytics-as-a-service. Not a startup — an
open-source library.

## Related work

The generic-tracing space is crowded and mature. `loopcanary` is
not trying to be a general observability platform; the niche is
narrower and deliberately so.

- **LangSmith / Weave / Arize Phoenix / Braintrust** — mature
  LLM-tracing platforms. `loopcanary` differs by focusing on
  named degradation detectors and compression / memory event
  surfacing rather than generic event capture.
- **Inspect AI** (UK AISI) — Python eval framework with monitoring
  hooks. `loopcanary` is complementary; a future release may ship
  an Inspect AI adapter.
- **[`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress)** —
  the sibling research harness. Where loopcanary's `metr_safety`
  detector reuses METR's reward-hacking prompt, monitorstress is
  where that monitor's robustness is studied empirically (the SaTML
  finding). Separate repo; not a dependency.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Issue reports and
discussion are welcome before v1.0 lands; **API-shape feedback is
especially valuable right now** because the public surface locks
under semver at the v1.0 tag.

## Documentation

- [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md) — v1.0
  plan, scope, roadmap, competition, risks, open questions
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — where the
  project is right now (kept fresh across sessions)
- [`docs/COLLAB_CONTEXT.md`](docs/COLLAB_CONTEXT.md) — framing
  history and owner preferences for AI collaborators working across
  sessions
- [`docs/SESSION_PROTOCOLS.md`](docs/SESSION_PROTOCOLS.md) —
  cross-session AI-assisted development discipline
- [`CHANGELOG.md`](CHANGELOG.md) — release notes
- The project's pre-pivot history, the batch experiments, the
  diagnostic trail, and the research finding moved to the
  [`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress)
  repository during the two-repo split.

## License

MIT — see [`LICENSE`](LICENSE). Cite as
`Zhang, T. (2026). loopcanary.`
https://github.com/tianyi-zhang-02/loopcanary
