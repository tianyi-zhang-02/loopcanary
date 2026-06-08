# Collaboration Context

*This file is for AI agents (Claude Code, Claude.ai chat) collaborating on monitorstress across sessions. Read at the start of every new session, alongside `docs/PROJECT_STATE.md`.*

## Project pitch (one sentence)

monitorstress is a CLI stress-test runner for AI safety monitors — given labelled agent trajectories, it applies structural transformations, runs the chosen monitor on every variant, and reports per-transformation performance degradation.

## Framing history (why the project is shaped the way it is)

- **Original framing (Phase 0, pre-pivot):** A multi-layer benchmark-integrity audit framework with three independent layers (Layer 1 Docker workspace replay, Layer 2 AST syntactic exploit detection, Layer 3 LLM-as-judge with multi-tier escalation), emitting a structured `AuditVerdict` with per-layer provenance. The pre-pivot docs (`architecture.md`, `exploit-taxonomy.md`, `related-work.md`, `examples/README.md`) describe this framing; PR #1 marks them SUPERSEDED.
- **Pivot trigger:** Primary-source reading (`docs/reading_notes.md`) showed that Griffin et al. (UK AISI Control Team, Aug 2025) already occupy the (A-prime) calibrated-classifier-on-MALT space; METR's monitor numbers are at 0.96 AUROC ceiling for reward-hacking on unobfuscated data; the debate-literature framing for "measurement substrate for scalable oversight" is rhetorical rather than load-bearing.
- **Current framing (v0.1):** A reformulated (D) — standardised stress-test evaluation suite for post-hoc agent integrity monitors. Calibration is one dimension among several (point AUROC, Δ AUROC under transformation, FPR shift at calibrated threshold). The contribution is *comparison across monitors and transformation conditions on a stable substrate*, not building a better monitor or being first to publish calibration numbers. Recommendation came at **medium** confidence in `docs/pivot_decision.md`.
- **v0.1 scope:** One monitor (METR's published prompt), one corpus (MALT public split, 1,826 manually-reviewed rows), three structural transformations. Semantic transformations and additional monitors are v0.2+.

## Owner preferences

Inferred from the working history visible in this repo and the standing-rules turns from prior sessions:

- **Audience target.** Anthropic Fellows applications, mentioned explicitly in the original status-report request ("would I be comfortable showing an Anthropic Fellows reviewer"). Workshop paper + working tool valued over main-conference targeting with no shipped artefact.
- **Communication discipline.** Brief, signal-dense responses preferred. The 3-line summary format (readiness / risk / top next action) is used as the top-level handoff format throughout this project. Nested compression layers (3-line → TL;DR → full report) are an established pattern.
- **In the loop, selectively.** Wants to be consulted on: pivots, framing decisions, governance changes, API spend, type-level changes with potentially wide blast radius (case (a) fixes), public artefacts. Does **not** want to be consulted on: routine implementation against a defined spec, tests/lint/types, factual doc corrections, feature-branch + PR mechanics.
- **Tool-first, paper second.** The project plan ships a working tool before a paper. Paper scope (workshop vs. main conference) is deferred until v0.2 empirical results inform the choice.
- **Honest negative results.** Q5 (Anthropic auth blocker in the sandbox) was documented as a real unmet deliverable rather than papered over. Phase 3 produced zero AUROC numbers; the docs say so. Documenting limitations is preferred over polished overclaiming.
- **Standing safeguards already established.** Never push to `main`; never force-push; never rewrite pushed history; never touch governance files (`LICENSE`, `SECURITY.md`, `.github/`, `pyproject.toml` `[project]` metadata) without explicit authorisation; never handle secrets; never operate outside the monitorstress working tree; never exceed per-session API budget. Full list in `docs/SESSION_PROTOCOLS.md`.

## Active research direction

Stress-test runner for safety monitors on MALT as the v1 contribution. v0.1 ships the smallest end-to-end vertical slice: three structural transformations, one monitor (METR's prompt), one corpus (MALT), one report card with bootstrap CIs. v0.2 adds semantic transformations (CoT vague-ification, summarisation) and additional monitors (EvilGenie reproduction, cascaded multi-tier). Paper scope is deferred until v0.2 empirical results inform the workshop-vs-conference choice; the decision logic is "ship a thing, learn from it, then decide what the thing means."

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
