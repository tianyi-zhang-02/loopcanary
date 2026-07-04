# Collaboration Context

*This file is for AI agents (Claude Code, Claude.ai chat) collaborating on loopcanary across sessions. Read at the start of every new session, alongside `docs/PROJECT_STATE.md`.*

## Project pitch (one sentence)

`loopcanary` is an open-source Python library for **agent-loop
observability** that diagnoses when an agent's behaviour is degrading,
its context is compressing, or its cost is running away — via a
`with ms.watch(...) as run:` context manager that runs pluggable
detectors against the trajectory as it streams. (v1.0 target;
implementation not yet started as of 2026-06-08. See "Framing history"
below for what came before and the pivot to this shape.)

## Framing history (why the project is shaped the way it is)

- **Original framing (Phase 0, pre-pivot #1):** A multi-layer
  benchmark-integrity audit framework with three independent layers
  (Layer 1 Docker workspace replay, Layer 2 AST syntactic exploit
  detection, Layer 3 LLM-as-judge with multi-tier escalation),
  emitting a structured `AuditVerdict` with per-layer provenance.
  The pre-pivot docs (`architecture.md`, `exploit-taxonomy.md`,
  `related-work.md`, `examples/README.md`) describe this framing;
  PR #1 marks them SUPERSEDED.
- **First pivot (v0.1 batch, 2026-05):** Reading of Griffin et al.
  (UK AISI Control Team, Aug 2025), Radharapu et al., and METR's
  MALT release (see `docs/reading_notes.md`) showed that the
  (A-prime) calibrated-classifier-on-MALT space was already
  occupied, METR's monitor numbers were at ceiling, and the
  debate-literature framing was rhetorical rather than load-bearing.
  Rec: reformulated (D) — a standardised stress-test suite for
  post-hoc agent integrity monitors. v0.1 shipped this: one monitor
  (METR's), one corpus (MALT public, 1,826 manually-reviewed rows),
  three structural transformations, one report card. See
  [`docs/pivot_decision.md`](pivot_decision.md).
- **Empirical results from v0.1:** Haiku n=60 with the faithful
  METR prompt (PR #6) collapsed to AUROC 0.517 (chance). Sonnet
  n=60 with faithful prompt has not yet been executed — the
  `--model` flag from PR #7 enables it. So we know the batch tool
  can run; we don't yet know that it measures anything real. This
  ambiguity is a load-bearing factor in the second pivot.
- **Second pivot (v1.0 SDK, 2026-06-08):** Reframed from a batch
  CLI over saved trajectories to an **open-source Python library
  for streaming agent-loop observability**. Rationale in
  [`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md). Key argument:
  in 2026, the ecosystem has moved from *"benchmark, run your model
  on it"* to *"agent runtime, register your monitor as a callback"*;
  a batch CLI over saved MALT reads as pre-2025 shape. Distinctive
  OSS niche relative to LangSmith / Weave / Arize / Braintrust:
  **degradation diagnosis + compression/memory event surfacing**.
  Explicitly acknowledged in the plan that the pivot is
  *directionally right* but the evidence base is more "the field
  has moved" than "we tried the current shape and it demonstrably
  doesn't measure what we care about."
- **v1.0 scope (in development):** Python SDK, no dashboard, no
  service. Ships with Claude Agent SDK integration + a generic
  wrap-any-callable adapter (so LangChain users aren't locked out
  until v1.1). Six initial detectors, timeline report renderer,
  per-run JSON export. Full spec in
  [`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md).
- **What survives from v0.1:** `TrajectoryEvent` discriminated
  union, `SemanticVerdict` shape, METR prompt monitor
  (repositioned as one plug-in detector), `--model` flag +
  model-keyed pricing (PR #7), MALT adapter and AUROC report card
  (retained as validation infrastructure for the safety-detector
  plug-in specifically). What reshapes: CLI → SDK, batch →
  streaming, AUROC-vs-transformations report → degradation-timeline
  report. Structural transformations reshape as counterfactuals.

## Owner preferences

Inferred from the working history visible in this repo and the standing-rules turns from prior sessions:

- **Audience target.** Anthropic Fellows applications, mentioned explicitly in the original status-report request ("would I be comfortable showing an Anthropic Fellows reviewer"). Workshop paper + working tool valued over main-conference targeting with no shipped artefact.
- **Communication discipline.** Brief, signal-dense responses preferred. The 3-line summary format (readiness / risk / top next action) is used as the top-level handoff format throughout this project. Nested compression layers (3-line → TL;DR → full report) are an established pattern.
- **In the loop, selectively.** Wants to be consulted on: pivots, framing decisions, governance changes, API spend, type-level changes with potentially wide blast radius (case (a) fixes), public artefacts. Does **not** want to be consulted on: routine implementation against a defined spec, tests/lint/types, factual doc corrections, feature-branch + PR mechanics.
- **Tool-first, paper second.** The project plan ships a working tool before a paper. Paper scope (workshop vs. main conference) is deferred until v0.2 empirical results inform the choice.
- **Honest negative results.** Q5 (Anthropic auth blocker in the sandbox) was documented as a real unmet deliverable rather than papered over. Phase 3 produced zero AUROC numbers; the docs say so. Documenting limitations is preferred over polished overclaiming.
- **Standing safeguards already established.** Never push to `main`; never force-push; never rewrite pushed history; never touch governance files (`LICENSE`, `SECURITY.md`, `.github/`, `pyproject.toml` `[project]` metadata) without explicit authorisation; never handle secrets; never operate outside the loopcanary working tree; never exceed per-session API budget. Full list in `docs/SESSION_PROTOCOLS.md`.

## Active research direction

**Agent-loop observability library** targeting the open-source Python
community. The v1.0 contribution is a `pip install loopcanary`
library that ships with `with ms.watch(...) as run:` as its primary
integration surface, six initial detectors (five zero-cost
behavioural + one LLM-call safety detector wrapping the METR prompt),
and a per-run timeline report. Anchor framework: Claude Agent SDK,
with a generic wrap-any-callable API alongside for LangChain reach.

The distinctive OSS niche relative to LangSmith / Weave / Arize
Phoenix / Braintrust is **named degradation detectors** (structured
signals for loop-of-death, null progress, cost run-away, context
pressure, compression cadence) plus **compression / memory event
surfacing** (Claude's auto-compact and similar behaviours made
visible and correlated with downstream outcomes). "Generic tracing"
is not the niche — a lot of well-funded teams already do that better
than a solo project can.

Full plan: [`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md). Paper
scope is deferred until v1.0 ships and has demonstrable users; the
decision logic remains "ship a thing, learn from it, then decide
what the thing means."

## Things to stop and ask about, not act on

- Anything that changes project framing or scope (pivots, contribution claim, target venue).
- Anything that touches governance files: `LICENSE`, `SECURITY.md`, `.github/`, `pyproject.toml`'s `[project]` metadata block (name, version, license, authors), `CODEOWNERS`.
- Anything involving API spend beyond the explicit per-session budget cap.
- Anything that creates public artefacts: GitHub releases, version tags, social previews, README rewrites of the headline framing.
- Type-level changes whose blast radius might extend to every producer of a value (e.g., adding validators to `Trajectory`, `SemanticVerdict`, `ScoreRecord`).
- Anything ambiguous in spec that would require a judgment call.

## Things to do without asking

- Standard implementation against a defined spec.
- Tests, lint runs, type checks, formatter runs.
- Doc corrections for factual errors (e.g., the 2,690 → 1,826 MALT row count correction).
- Feature branches (`claude/<task>` convention) and PRs against `main`.
- Adding tests to cover gaps surfaced by reviews.
- Status reports, root-cause investigations, structured handoff messages.

## Session protocols

See `docs/SESSION_PROTOCOLS.md`.
