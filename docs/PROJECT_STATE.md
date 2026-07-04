# Project State

*Last updated: 2026-06-08, by Claude Code session. Branch base:
`63669fd` (origin/main tip, PR #8 pivot plan merged). Pivot to
agent-loop observability accepted; implementation not yet started.*

## Identity

`monitorstress` is transitioning from **"batch CLI that
stress-tests AI safety monitors on saved MALT trajectories"**
(v0.1, on `main`, functional) to **"open-source Python library for
agent-loop observability with named degradation detectors and
compression / memory event surfacing"** (v1.0, in development).

Canonical spec for v1.0: [`docs/pivot_v1_agentic.md`](pivot_v1_agentic.md).

## Current phase

**Post-pivot-acceptance, pre-v1.0-implementation.** The pivot plan
merged as PR #8 (`63669fd`). This restructure PR then updates
governance docs (README, PROJECT_STATE, COLLAB_CONTEXT, SUPERSEDED
markers on pre-pivot content) to catch the repo up with the new
direction. No v1.0 code has landed. The v0.1 batch shape remains
runnable on `main`.

## Active work

- **This PR (branch `docs/pivot-restructure`)** — README rewrite,
  PROJECT_STATE / COLLAB_CONTEXT refresh, SUPERSEDED markers on
  pre-pivot docs, commit the three uncommitted diagnosis docs as
  historical record, add CONTRIBUTING and CHANGELOG placeholders.
  **Owner: Tianyi** (review). No code changes; no rename; no
  directory restructure.
- **Pending: v0.1 Sonnet re-run (Q5-adjacent).** Pre-v1.0-code
  prerequisite from the pivot plan. Runs on Tianyi's local shell
  (sandbox has no working Anthropic credentials). Confirms whether
  the batch shape can measure anything real, which informs how
  aggressive to be in the v1.0 architectural break from v0.1's
  assumptions. Estimated cost ~$0.90.

## Open decisions

- **Package rename before v1.0?** `monitorstress` reads as a
  benchmark tool; the pivot plan discusses discoverability for OSS
  distribution. Shortlist: `driftlens`, `looplens`, `agentgaze`,
  `agentscope`, `driftwatch`, or keep `monitorstress` (double
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
  `trajaudit` (arXiv name collision) to `monitorstress`.
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
