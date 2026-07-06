# Project State

*Last updated: 2026-07-05, by Claude Code session. Two-repo split
executed: this repo (`loopcanary`) is now the SDK tool, seeded with
the data model; the batch harness + SaTML finding moved to the
separate `monitorstress` repo.*

## Identity

`loopcanary` is an **open-source agent-loop observability SDK** (in
development): named degradation detectors + compression/memory event
surfacing over an agent's execution loop, via a `watch()` context
manager. **Tool, not paper** — success is software metrics (installs
cleanly, hooks into a loop in a few lines, honest README, people use
it), not novelty. No paper obligation is attached to this repo.

This repository currently holds the **data-model seed** —
`src/loopcanary/core/` (`TrajectoryEvent`, `Trajectory`,
`SemanticVerdict`). The v1.0 SDK surface is specified in
[`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md) and not yet built.

**Sibling repo:** [`monitorstress`](https://github.com/tianyi-zhang-02/monitorstress)
— the research harness for the SaTML CoT-monitor-robustness paper
(the batch CLI, MALT, transformations, the finding). Independent;
neither repo imports the other.

## Current phase

**Post-split, pre-v1.0-implementation.** The two-track decision
(2026-07-05) separated the SDK (this repo) from the research harness
(monitorstress repo). This repo was stripped to the data model +
SDK plan. No SDK code (`watch`, detectors) has landed yet.

## Active work

- **This PR (branch `split/strip-to-sdk-seed`)** — strips loopcanary
  to the SDK seed: removes the batch harness (now in monitorstress),
  slims deps to `pydantic`, rewrites `__init__` / README / pyproject
  for the SDK framing. **Owner: Tianyi** (review + merge — freeze holds).
- **Next: build the v1.0 SDK** per `docs/pivot_v1_agentic.md` —
  extended `TrajectoryEvent` variants → `Detector` protocol →
  `watch()` context manager → Anthropic-SDK instrumentation. Not
  started.
- **Research track (separate repo, hard Sept-29 clock):** the
  `drop_reasoning`→chance finding lives in `monitorstress`; the
  ship-vs-strengthen decision is open there. Does **not** block or
  depend on this repo.

## Open decisions

- **Package rename before v1.0?** `loopcanary` reads as a
  benchmark tool; the pivot plan discusses discoverability for OSS
  distribution. Shortlist: `driftlens`, `looplens`, `agentgaze`,
  `agentscope`, `driftwatch`, or keep `loopcanary` (double
  meaning). See
  [`pivot_v1_agentic.md#open-source-distribution-considerations`](pivot_v1_agentic.md).
  Cost of renaming again is real (last rename was PR #5's six-commit
  cross-file cleanup); OSS discoverability benefit is also real.
  Decision required before v1.0 tag.
- **Implementation ordering.** The pivot plan lists four code commits
  (extended events → detector protocol → `watch` context manager →
  Anthropic SDK instrumentation). Tianyi picks when to start; the
  Sonnet re-run gates the first commit.
- **Anchor framework details for v1.0 launch.** Plan says Claude
  Agent SDK primary + generic wrap-any-callable alongside. Concrete
  API-surface choices need a final review before code lands, per
  the semver commitment at v1.0 tag.

## Active blockers

- **v1.0 code prerequisites.** Sonnet n=60 re-run (owner: Tianyi
  local) and rename decision (owner: Tianyi) both gate the first
  v1.0 implementation commit.

## Recently completed (last 30 days)

- **PR #8 — pivot plan accepted** (`63669fd`). Merged the
  agent-observability direction change and its OSS-distribution
  addendum. Load-bearing artefact for all subsequent work.
- **PR #7 — `--model` flag + model-keyed pricing + run-output
  records model id** (`6b99985`). Anti-footgun infrastructure so
  "which model ran" is a verifiable fact in every run's output JSON.
- **PR #6 — prompt verbatim parity with METR's published version**
  (`90d4d62`). Added the four missing blocks (negative examples,
  `<first_few_messages>` / `<transcript_chunk>` XML delimiters,
  "if you are unsure" hint, closing reinforcement); wrote and
  independently verified via `docs/prompt_parity_verification.md`.
- **PR #5 — repository and package rename** (`bd48601`), from
  `trajaudit` (arXiv name collision) to `loopcanary`.
- **PR #4 — Anthropic monitor migrated to Claude Haiku 4.5** with
  correct pricing.

## What's NOT in this project (anti-scope)

**Preserved from the pre-pivot list:**

- Semantic transformations (CoT vague-ification, summarisation).
- SWE-bench / Terminal-Bench / WebArena / GAIA / OSWorld adapters.
- Layer 1 Docker sandbox / Layer 2 syntactic scanner.

**Added by the pivot:**

- Hosted dashboard / hosted anything (T3 aspirational, out of solo
  scope).
- Team collaboration / multi-user features.
- Cross-run analytics as a service.
- Non-Anthropic-SDK integrations before v1.1 (except a lightweight
  "wrap any callable" adapter that ships alongside v1.0's Claude
  Agent SDK primary integration).
- Paper writeup before shipping working v1.0.

## Pointers

- [`README.md`](../README.md) — user-facing entry, v1.0-facing.
- [`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md) — v1.0 plan,
  canonical spec.
- [`docs/COLLAB_CONTEXT.md`](COLLAB_CONTEXT.md) — collaboration
  context and framing history for AI-agent sessions.
- [`docs/SESSION_PROTOCOLS.md`](SESSION_PROTOCOLS.md) — start/end-of-session
  operational protocols.
- [`docs/followups.md`](followups.md) — non-blocking follow-ups.
- [`docs/auto_session_questions.md`](auto_session_questions.md) —
  open questions from autonomous sessions.
- Historical decision records preserved as SUPERSEDED:
  [`spec.md`](spec.md),
  [`architecture.md`](architecture.md),
  [`related-work.md`](related-work.md),
  [`exploit-taxonomy.md`](exploit-taxonomy.md),
  [`pivot_decision.md`](pivot_decision.md) (the earlier
  multi-layer → stress-test pivot),
  [`repo_audit.md`](repo_audit.md),
  [`refactor_summary.md`](refactor_summary.md),
  [`malt_recon.md`](malt_recon.md),
  [`reading_notes.md`](reading_notes.md),
  [`status_report.md`](status_report.md),
  plus the batch-shape diagnostic trail
  ([`score_parser_diagnosis.md`](score_parser_diagnosis.md),
  [`prompt_and_format_diagnosis.md`](prompt_and_format_diagnosis.md),
  [`prompt_parity_verification.md`](prompt_parity_verification.md)).
