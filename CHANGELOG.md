# Changelog

All notable changes to this project will be documented in this file. The
format loosely follows [Keep a Changelog](https://keepachangelog.com/),
and versioning follows [SemVer](https://semver.org/) — with the caveat
that no version has been tagged yet.

## [Unreleased]

### Changed
- **Direction pivot (2026-06-08):** From a batch CLI that stress-tests
  AI safety monitors on saved MALT trajectories to an open-source
  Python library for streaming agent-loop observability. Full plan in
  [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md). No v1.0 code
  has landed yet; the v0.1 batch shape remains runnable on `main`.
- **README rewritten** to reflect the pivot; the batch prototype
  install instructions are preserved in a "Running the v0.1 batch
  prototype (today)" section.
- **`docs/PROJECT_STATE.md` refreshed** to describe the post-pivot
  state.
- **`docs/COLLAB_CONTEXT.md` framing history extended** with the
  second pivot (batch → SDK) alongside the earlier pivot
  (multi-layer → batch).
- **`docs/spec.md` marked SUPERSEDED** — content preserved as the
  accurate description of what the v0.1 CLI still does, and as
  decision history.
- **`CONTRIBUTING.md` rewritten** to match the current framing and
  the "API-shape feedback is more valuable than premature PRs" stance
  for the pre-v1.0 window.

### Added
- **`docs/pivot_v1_agentic.md`** (PR #8) — canonical v1.0 spec.
- **`docs/score_parser_diagnosis.md`,
   `docs/prompt_and_format_diagnosis.md`,
   `docs/prompt_parity_verification.md`** — batch-shape diagnostic
  reports, committed as historical decision records.
- **`CHANGELOG.md`** (this file).

## Pre-v1.0 milestones (recorded here for reference — not tagged
versions)

- **PR #7 — `--model` flag + model-keyed pricing + run-output records
  model id** (`6b99985`, 2026-06-08). Anti-footgun infrastructure so
  "which model ran" is a verifiable fact in every run's output JSON.
- **PR #6 — prompt verbatim parity with METR's published version**
  (`90d4d62`, 2026-06-08). Added the four missing blocks (negative
  examples, XML delimiters, "if you are unsure" hint, closing
  reinforcement). Independently verified via
  `docs/prompt_parity_verification.md`.
- **PR #5 — repository and package rename** (`bd48601`, 2026-05-31),
  from `trajaudit` (arXiv name collision) to `monitorstress`.
- **PR #4 — migrated Anthropic monitor to Claude Haiku 4.5** with
  correct pricing.
- **PR #3 — mockup labelling in README** so no reader could confuse
  illustrative numbers with real results.
- **PR #2 — project-memory infrastructure**
  (`docs/PROJECT_STATE.md`, `docs/COLLAB_CONTEXT.md`,
  `docs/SESSION_PROTOCOLS.md`) for cross-session AI-assisted
  development.
- **PR #1 — v0.1 batch CLI** (MALT adapter, three structural
  transformations, Monitor protocol + METR implementation, CLI
  entrypoint, report card).
