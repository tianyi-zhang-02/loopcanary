# v1.0 pivot proposal — from batch monitor-stress-testing to agent-loop observability

*Written 2026-06-08. Awaits Tianyi's review before any code lands. Nothing else changed in the repo yet; this is a spec on a branch, not an implementation.*

## TL;DR (60 sec)

Repivot from **"CLI that stress-tests safety monitors on saved MALT
trajectories"** to **"Python SDK that watches an agent's execution
loop and diagnoses when its behaviour is degrading, its memory is
compressing, or its cost is running away."** The current codebase's
data model (`TrajectoryEvent` discriminated union, `SemanticVerdict`
shape, MALT adapter, METR prompt monitor) carries over more than
you'd guess — none of it is wasted. What reshapes is the *outer
shell*: batch CLI → streaming instrumentation, offline AUROC report
→ degradation timeline, structural transformations → counterfactual
replays. The distinctive niche vs. LangSmith / Weave / Arize /
Braintrust is **degradation diagnosis + compression / memory event
surfacing**; without that anchor we're building a worse LangSmith.

**One recommendation to accept before we go further:** target Tier 1
(Python SDK, no dashboard, no service) as v1.0. It ships in weeks,
it's a defensible Fellows-application artefact on its own, and T2
(local dashboard) is a follow-on rather than a competing rewrite.

## Why this pivot

**Evidence supporting the pivot:**

- **The field has moved.** In 2026 the ecosystem around agent
  evaluation has largely shifted from *"here's a static benchmark,
  run your model on it"* to *"here's an agent runtime, register your
  monitor as a callback."* Inspect AI, LangSmith, Weave, and
  Anthropic's own Managed Agents / Console all operate in the
  streaming-instrumentation mode. A batch-CLI-over-saved-MALT tool
  reads as pre-2025 shape.
- **The interesting problems are not the current problems.** The
  most consequential agent-safety failures in the wild today aren't
  "did the monitor's AUROC recover" — they're loop-of-death, silent
  context compression that drops the constraint the user set at step
  1, memory writes that don't recall later, cost run-away in long
  loops. None of those are measurable from a saved MALT transcript
  in one shot.
- **The current codebase's biggest asset is its data model.** The
  `TrajectoryEvent` discriminated union (`ReasoningEvent`,
  `ToolCallEvent`, `ObservationEvent`, `ScoringEvent`) is *actually
  well-suited* for streaming instrumentation. Adding
  `CompressionEvent`, `MemoryWriteEvent`, `MemoryReadEvent`,
  `ContextSizeCheckpoint` is a one-PR extension. The refactor that
  landed in commits `9aa2160..146aa3b` turns out to have been the
  right move *for a different use case than it was made for*.

**Evidence NOT supporting the pivot — do not paper over this:**

- **The current tool has not yet been validated against a working
  monitor.** Haiku n=60 with the faithful METR prompt collapsed to
  AUROC 0.517 (chance). Sonnet n=60 has never run (silent-swap bug,
  now fixed by PR #7 but not yet re-executed). We don't know if the
  batch shape works — we know it hasn't been *made to* work yet.
  Pivoting before finishing that diagnostic is a live risk.
- **Observability platforms are a mature, well-funded, crowded
  space.** LangSmith, Weave, Arize Phoenix, Braintrust each has a
  team + years of engineering + a paying user base. A solo project's
  chance of winning on generic tracing is zero. The pivot only makes
  sense if we lean hard into the *degradation-diagnosis + compression
  visibility* niche that those tools cover weakly.
- **The pivot doubles the scope of things to build.** T1 alone is
  ~10× the surface of the current CLI. Realistic delivery timing has
  to plan for this.

**Honest read on whether this pivot is well-founded or premature:**
mixed. The framing shift is *directionally* right — agentic
observability is where the interesting questions live — but the
evidence base is more "the field has moved" than "we tried the
current shape and it demonstrably doesn't measure what we care
about." That distinction matters: if we're pivoting because the
batch shape is fundamentally wrong-for-the-market, the pivot is
sound. If we're pivoting because debugging the batch shape is
frustrating, it's procrastination in disguise.

**Mitigation.** Finish PR #7's Sonnet re-run *before* landing the
first code commit on the pivot. If Sonnet-with-faithful-prompt
recovers to METR's neighbourhood, we have evidence that the batch
shape can work, and pivoting is a market-shape decision (defensible).
If Sonnet also collapses, we have evidence that the batch shape has
deeper issues; the pivot is more urgent AND we should be careful not
to rebuild the same issues in the new shape.

## What the tool becomes

**One paragraph pitch:**

`loopcanary` is a Python SDK that instruments an agent's
execution loop and tells you when its behaviour is degrading. It
captures every reasoning step, tool call, observation, memory
write, and compression event. It runs pluggable detectors (safety
monitors like METR's, plus behavioural detectors like repeated
actions, null-progress plateaus, context pressure, cost burn-rate)
against the trajectory as it streams. It emits a timeline report
that shows when detectors fired, what preceded each fire, and how
cost / tokens / context / memory-state evolved. The v1 release is
a library you `import`, not a service you deploy; ~200 lines of
integration on top of a Claude Agent SDK client is enough to
instrument a real production loop.

**Who uses it:**

- Someone running a long-running agent loop (research assistant,
  coding agent, workflow automator) who needs to know *when it starts
  going off the rails* mid-run.
- Someone red-teaming their own agent's degradation modes before
  ship.
- Someone doing safety-oriented research on agent monitoring
  behaviour longitudinally, where the existing "score the finished
  transcript" tools don't help.

## What survives from loopcanary-batch (more than you'd guess)

| Component | Fate | Notes |
|---|---|---|
| `TrajectoryEvent` discriminated union | **Reused, extended** | Adds `CompressionEvent`, `MemoryWriteEvent`, `MemoryReadEvent`, `ContextSizeCheckpoint`. The design decision to make events discriminated pays off exactly here. |
| `SemanticVerdict` shape (score + abstain + reasoning) | **Reused** | Same shape works for every detector's output — safety monitor, behavioural detector, cost detector. Abstain remains first-class. |
| `TaxonomyTag` enum | **Extended** | Add behavioural-degradation categories (`repeated_action`, `null_progress`, `context_pressure`, `cost_burn`, `compression_event`). |
| `M1 invariant` on `ScoreRecord` | **Reused via new record shape** | The `(monitor_score is None) ⟺ abstain` invariant still holds; extends naturally to per-detector signals. |
| METR prompt monitor (`loopcanary.monitors.metr_prompt`) | **Reused, reshaped** | Becomes one plug-in detector. Its verbatim METR prompt work (PR #6) stands. Instead of running once over the whole trajectory, it runs periodically over the trajectory-so-far (which happens to match METR's actual chunked operational model — see `docs/prompt_and_format_diagnosis.md`). This is a **latent-benefit** of the pivot. |
| `--model` flag + model-keyed pricing (PR #7) | **Reused** | Every detector that calls an LLM inherits the pricing lookup. Cost tracking becomes central to the new report, not a side feature. |
| MALT adapter | **Kept for validation** | MALT becomes the validation corpus for the safety-detector plug-in specifically (does our METR-prompt detector actually detect reward hacking?), not the main data source. |
| Structural transformations (`drop_reasoning`, `truncate_observations`, `pad_with_noops`) | **Reshaped as counterfactuals** | Instead of *"stress-test the monitor"* they become *"replay this run with the compression event at step 30 removed — what would the safety detector have said?"* This is arguably a more interesting research question than the original framing. |
| Bootstrap-CI / AUROC report card | **Kept for validation, not for main report** | Same reuse story as MALT — used for validating the safety detector on the MALT corpus, not for the main per-run observability report. |
| CI, test infrastructure, `pytest`+`ruff`+`mypy` discipline | **Reused wholesale** | Zero change. |

## What reshapes / gets removed from loopcanary-batch

| Component | Fate | Notes |
|---|---|---|
| CLI `loopcanary run` command | **Reshaped** | Becomes `loopcanary.watch(agent)` as a context manager or decorator. A thin CLI `loopcanary replay <run-json>` might survive for post-hoc analysis. |
| Batch execution model | **Removed** | The main data flow is now streaming, not batched over MALT. |
| Report card semantics (AUROC vs. transformations) | **Removed from main report** | Replaced with a **timeline visualisation** — steps × events × detector fires × cost/tokens/context. AUROC math survives only for the safety-detector-on-MALT validation piece. |
| Fixture-based MALT tests as the primary test suite | **Reshaped** | Still exist for the safety-detector validation piece. But the primary test suite becomes agent-loop instrumentation tests — mock an agent, feed it events, assert the detectors fire correctly. |
| Docs positioning the project as a "stress-test runner" | **SUPERSEDED headers added** | `docs/spec.md`, `docs/COLLAB_CONTEXT.md`, `docs/PROJECT_STATE.md`, `README.md`, and the diagnosis docs all get a note that they describe the pre-pivot shape. Content stays as decision history, same convention used for the earlier multi-layer→stress-test pivot. |

## v1.0 scope — Tier 1 (concrete, in-scope)

**Delivery: Python SDK. No dashboard, no service, no persistence
beyond the per-run JSON output.**

### Core SDK surface

Three integration modes, in decreasing order of ergonomic priority:

```python
# 1. Context manager (recommended)
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

# run.report is now populated; render or serialise it
run.report.render()

# 2. Instrumentation on the Anthropic SDK client
from anthropic import Anthropic
client = ms.instrument(Anthropic(), detectors=[...])
# every client.messages.create(...) is captured

# 3. Decorator on an agent-run function
@ms.watch(detectors=[...])
def run_task(agent, task):
    return agent.run(task)
```

### Extended data model

New `TrajectoryEvent` variants:

- `CompressionEvent(before_tokens: int, after_tokens: int, method: str)` — a context compression happened (either Claude's auto-compact, or an explicit summariser call, or a caller-driven truncation)
- `MemoryWriteEvent(key: str, value_snippet: str, size_bytes: int)`
- `MemoryReadEvent(key: str, found: bool, size_bytes: int)`
- `ContextSizeCheckpoint(input_tokens: int, output_tokens_so_far: int, timestamp: datetime)` — periodic checkpoint of context usage, emitted automatically by the instrumentation layer

`SemanticVerdict` gains no new fields — its (score, abstain, reasoning, confidence_band, taxonomy_tags) shape already works.

### Detector protocol

```python
from typing import Protocol
from loopcanary.core.trajectory import Trajectory
from loopcanary.core.verdict import SemanticVerdict

class Detector(Protocol):
    name: str

    def check(self, trajectory_so_far: Trajectory) -> SemanticVerdict | None:
        """Called after each new event. Return a verdict to raise a
        signal, or None to stay silent. May be called many times per
        run — implementations must be cheap."""
        ...
```

### Initial detector set

- **`repeated_action(threshold: int = 3)`** — same tool call with identical arguments fires `threshold` times in a row. Zero-cost detector.
- **`context_pressure(warn_at: float = 0.8)`** — input tokens exceed `warn_at * model.context_window`. Zero-cost detector.
- **`cost_burn_rate(usd_per_min_max: float)`** — spend velocity above threshold. Zero-cost detector.
- **`null_progress(window_steps: int = 5)`** — no observable state change (no new file writes, no unique tool calls, no memory writes) over `window_steps` steps. Zero-cost detector.
- **`compression_frequency(max_per_hour: int)`** — CompressionEvents firing above rate threshold. Zero-cost detector.
- **`metr_safety(model: str = "haiku", every_n_steps: int = 5)`** — the existing METR prompt monitor from `src/loopcanary/monitors/metr_prompt.py`, run periodically over the trajectory-so-far. This is the only initial detector that costs money to run.

### Report shape

```json
{
  "run_id": "...",
  "agent_id": "...",
  "started_at": "...",
  "ended_at": "...",
  "model": "claude-haiku-4-5-20251001",
  "total_cost_usd": 0.42,
  "total_input_tokens": 12340,
  "total_output_tokens": 5670,
  "detector_fires": [
    {"detector": "repeated_action", "at_step": 27, "verdict": {...}},
    {"detector": "metr_safety", "at_step": 30, "verdict": {...}}
  ],
  "events": [...],
  "checkpoints": [
    {"step": 10, "cost_usd": 0.10, "input_tokens": 3400, "context_pct": 0.31},
    ...
  ],
  "compression_events": [
    {"at_step": 25, "before_tokens": 45000, "after_tokens": 8000, "method": "auto-compact"}
  ]
}
```

Rich TUI renderer produces a timeline: `step | events | detectors | $ | ctx%`.

### Anchor framework for v1

**Claude Agent SDK.** Rationale:

- Matches the Anthropic-Fellows audience.
- Anthropic's SDK exposes callback hooks that a wrapper library can plug into cleanly.
- Auto-compaction — the load-bearing compression event we want to surface — is a Claude-specific behaviour where Anthropic's own tooling has limited visibility.

LangChain integration is a v1.1 nice-to-have. LlamaIndex and others land as follow-ons if there's demand.

## v2.0 (Tier 2, later, out of v1 scope)

- Local TUI dashboard (rich-based) showing detector timeline live during agent execution
- Multi-run comparison view (compare two runs of the same agent side-by-side; what changed?)
- Persistent local store (SQLite) so runs accumulate over time
- Web dashboard as a static HTML export

## v3.0 (Tier 3, aspirational, out of Fellows-solo-project scope)

- Hosted service with cross-run analytics
- Team + org accounts
- Integration with production observability stacks (Datadog, OpenTelemetry)

Not planning for T3 unless the project acquires a co-founder.

## Competition and differentiation

**Existing generic-tracing tools:** LangSmith (LangChain), Weave (W&B),
Arize Phoenix (LLM observability), Braintrust (evals-first), Anthropic
Console (Claude-specific per-request usage). All of these do
event-capture + cost tracking + timeline rendering. All of them are
larger, better-resourced, and further ahead than loopcanary will
be for years.

**Where they are weak / underserved:**

1. **Degradation diagnosis.** They record events but they don't
   *name* when the agent is going off-rails. "Cost went up" and "same
   tool fired 10 times" are visible in their timelines but not
   flagged as first-class signals with structured detector outputs.
2. **Compression / memory event surfacing.** Claude's auto-compact
   is opaque to most users; LangSmith etc. don't currently surface
   it as a first-class event because it happens inside Anthropic's
   API layer. Correlating compression with downstream degradation is
   an underexplored area.
3. **Safety monitoring as a plug-in detector.** These tools have
   quality scorers but not safety monitors. Making METR's
   reward-hacking monitor (and future monitors) usable as inline
   detectors is a distinct research contribution.

**Where they are strong and we should not compete:**

- Generic tracing (span capture, distributed tracing, replay UI).
- Team collaboration / permissions.
- Anything requiring hosted infrastructure.

**Framing risk.** If we describe loopcanary as "agent observability," reviewers hear "LangSmith with fewer features." If we describe it as **"the agent-loop degradation and compression diagnostician,"** the niche is legible and defensible. Copy discipline matters here — see the personal-doc reminder about marketing-mode framing (`personal_ops.md` §"Conversation patterns to watch for in myself"). Write about what's true and specific, not about the platform we haven't earned.

## Risks and open questions

**Risks:**

- **Scope creep.** Degradation + memory + compression + cost + safety monitoring in one v1 is a lot of surfaces. Prioritise ruthlessly — the initial detector set above is deliberately minimal.
- **The current tool hasn't been validated.** See the pivot-timing mitigation above: do Sonnet re-run first.
- **Anthropic Console might quietly ship auto-compact visibility.** If they do, the "we surface compression" differentiator weakens. Adjacent risk: hard to detect compression events from outside the Anthropic API — may need heuristics (context-token count dropping between calls) rather than a first-class hook.
- **The safety-monitor angle is orthogonal to most users' needs.** People who want observability aren't the same crowd as people who want reward-hacking detection. Framing has to accommodate both without confusing either.

**Open questions:**

1. **Which Sonnet re-run before committing to the pivot?** Do the n=60 first, decide whether to pivot based on the result. Recommended.
2. **Should we rename?** "loopcanary" reads as "stress-testing monitors" — accurate for the current shape, ambiguous for the new one. Options: keep (double meaning is fine), rename to something like `agentwatch` or `looplens` or `driftlens`. Renaming again is expensive (see the `trajaudit → loopcanary` rename PR trail); recommend defer until v1.1 unless the current name blocks the elevator pitch.
3. **Anchor framework — Claude Agent SDK first, LangChain second?** Or in parallel? Recommend: Claude Agent SDK first for tighter integration and audience match; LangChain adapter as v1.1.
4. **How does the pre-pivot batch mode survive?** Two options: (a) `loopcanary replay --input <MALT-corpus>` becomes a lightweight adapter that reuses the new detector framework over saved MALT trajectories — best of both worlds; (b) drop batch mode entirely. Recommend option (a): it costs little and preserves the MALT-validation story for the safety detector.
5. **Detector output vs. safety-monitor output — are they the same thing?** Currently `SemanticVerdict` is designed for safety monitors. Repurposing it for behavioural detectors ("this ran 3 times in a row") slightly stretches the semantics. Alternative: separate `DetectorSignal` type. Recommend: use `SemanticVerdict` for v1 to minimise data-model churn; reconsider if it turns out to be a poor fit for behavioural signals.

## Immediate next steps (if this plan is approved)

**Before any pivot code lands:**

1. **Run Sonnet n=60 with PR #7's `--model sonnet`.** Verify the current tool shape either does or doesn't measure something real. ~$0.90 spend. Whatever the result, capture it in a new diagnostic doc — either `docs/sonnet_n60_result.md` or a follow-up to `docs/prompt_and_format_diagnosis.md`.

**First pivot commit — no code, just governance:**

2. **Mark pre-pivot docs SUPERSEDED.** `docs/spec.md`, `docs/COLLAB_CONTEXT.md`, `docs/PROJECT_STATE.md`, `README.md`, and the three uncommitted diagnosis docs get `> SUPERSEDED. This describes the pre-pivot batch-CLI shape...` headers, pointing at this plan doc as the canonical current direction. Same convention as the earlier multi-layer→stress-test pivot's supersession pass. Do NOT delete or rewrite content — the audit trail is the point.

3. **Tag pre-pivot main.** `git tag v0.1-batch-shape 6b99985` (current main tip). Preserves the batch tool as a runnable historical artefact if anyone ever wants it back.

**First code commit — new data model:**

4. **Extend `TrajectoryEvent`** with `CompressionEvent`, `MemoryWriteEvent`, `MemoryReadEvent`, `ContextSizeCheckpoint`. This is a schema-only change, no runtime yet. Full test coverage on discriminator serialisation.

**Second code commit — detector protocol:**

5. **Define the `Detector` protocol** in `src/loopcanary/detectors/__init__.py`. Ship the first zero-cost detector (`repeated_action`) as the reference implementation. No agent-loop integration yet.

**Third code commit — the SDK entry point:**

6. **`loopcanary.watch()` context manager** that captures events (initially: hand-supplied by test callers, not yet from a live agent). Detectors registered against it fire on each new event. Report emitted at exit.

**Fourth code commit — first live integration:**

7. **Anthropic SDK instrumentation.** `ms.instrument(client)` wraps `messages.create()` to emit events into the currently-active `watch` context. This is where a live Claude Agent SDK run starts producing real detector fires.

Each of these commits is a small PR against `main`, reviewed and merged individually. The pivot doesn't ship as one giant rewrite.

## Open-source distribution considerations

*Added 2026-06-08 after Tianyi clarified the intent: this pivot is an
open-source community-serving tool, not an internal research artefact.*

This clarification changes several defaults in the plan above.

**API-surface bar rises.** *"Easy to plug into their workflow"*
means the acceptance test is: **`pip install loopcanary` → one
`import` → one context manager, working output within ten minutes on
a fresh machine.** No hidden config, no environment setup beyond
whatever the user already has for their agent runtime. The three
integration modes in the v1.0 SDK section stay, but the *default*
mode needs to be effortless. Every option beyond the default is a
tax on adoption.

**Documentation becomes the product.**

- `README.md` needs to be readable at a scan, install → first-fire in
  under 60 seconds of reader time. An animated GIF or screenshot of
  the timeline output at the top is worth building. Existing README
  (currently reflecting the batch stress-test framing) will need a
  full rewrite as part of the pivot — mark SUPERSEDED alongside
  `docs/spec.md`.
- `examples/` directory needs runnable scripts, one per major
  detector, one per integration mode. Currently empty (only a
  SUPERSEDED marker from the pre-pivot session). This becomes v1.0
  release-blocker work.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` all missing;
  standard OSS surface, cheap to add, expected by contributors.
  `LICENSE` (MIT) and `SECURITY.md` are already in place from the
  scaffold phase.

**Naming: reopened.** My earlier recommendation ("defer rename to
v1.1") was correct for an internal project but wrong for an
OSS-distribution project. Discoverability outweighs rename cost when
the audience is public. Shortlist:

| Candidate | Pros | Cons |
|---|---|---|
| `driftlens` | Invokes *drift* (the target) + *lens* (visibility). Clear niche. Under-claimed. | Both words already appear in adjacent tools; not unique enough |
| `looplens` | *Loop* (agent iteration) + *lens*. Directly names the "loop degradation" story. | Slightly generic |
| `agentgaze` | Memorable. Poetic. | Ambiguous meaning; may read as monitoring-of-users rather than monitoring-by-agent |
| `agentscope` | Reads as "scope for observing agents". Clear. | Overlap with "agent scope" in agent-framework discourse |
| `driftwatch` | Watchdog framing. Concrete verb. | Similar to `agentwatch`, may hit LangSmith-adjacent naming |
| Keep `loopcanary` | Zero cost. Double meaning (stress-testing monitors + stress-testing agents-with-monitors) is defensible. | Reads as a *benchmark*, not a *library*. SEO for "agent observability" is poor. |

**My recommendation:** `driftlens` or `looplens`. Both convey the
niche (degradation over time) without over-claiming a platform.
Decision is Tianyi's — the last rename (trajaudit → loopcanary)
had real cost (six commits, cross-file cleanup, external references
updated). Doing it *now*, before v1.0 code lands and before external
references accumulate, is meaningfully cheaper than doing it later.

**Anchor framework: broaden earlier.** The original recommendation
was "Claude Agent SDK first, LangChain in v1.1." For an OSS project
targeting broad reach, LangChain users being locked out until v1.1
is a real cost. Revised recommendation:

- **Primary integration:** Claude Agent SDK (as before) — tightest
  hooks, matches the Anthropic Fellows audience, gets the
  compression-event visibility story most cleanly since auto-compact
  is Claude-specific.
- **Alongside primary:** A generic "wrap any callable that produces
  a completion" API. Roughly 200 lines of code. LangChain users can
  use this immediately; a proper LangChain integration (chain-native
  instrumentation, agent-tool-callback wiring) can still wait for
  v1.1.

This resolves the tension between depth (Claude-SDK-specific
integration for the compression detector) and reach (LangChain users
shouldn't have to wait a version).

**Semantic-versioning commitment.** Once v1.0 tags, the public API
surface is locked. Breaking changes post-launch have real cost in an
OSS project. This means the SDK surface currently sketched in the
plan doc's v1.0 scope section needs a final API review *before* the
first code commit — not after users start depending on it. Concretely:
the `Detector` protocol shape, the event-type names, the `watch()`
context manager's signature, and the report JSON schema are the four
API-freeze surfaces.

**Launch surface (not today's problem, but a v1.0 blocker):**

- PyPI + GitHub with the anchor tagline "Diagnose when your agent's
  loop is degrading, its context is compressing, and its cost is
  running away." Not "observability platform."
- HN Show or equivalent around v1.0 release. Timing coordinates with
  the Anthropic Fellows application (per Tianyi's audience target).
- Twitter/X thread from Tianyi at release. Not before.
- Skip r/MachineLearning until there's real user substance — early
  posts to a critical audience with a proof-of-concept produce
  hostile reception more often than not.
- No blog post from Anthropic team unless one falls out of the
  Fellows-application process naturally.

**Community-tool discipline that stays out of scope for v1.0:**

- Hosted anything (T3 aspirational as before).
- Cross-run analytics (T2).
- Team collaboration / permissions (T3).
- Custom detector marketplace (interesting; wait for signal).
- Integrations beyond Claude Agent SDK + generic-callable + eventually
  LangChain (respond to actual demand, not anticipated demand).

## Explicit non-goals for v1

- No hosted dashboard.
- No cross-run analytics.
- No team collaboration features.
- No non-Anthropic-SDK integrations (LangChain waits for v1.1).
- No new monitor beyond the METR prompt monitor already in-tree.
- No paper writeup. Ship the tool first, decide what to write about later.
