# v1 scope (frozen)

The scope is frozen: implement everything in **IN SCOPE**, implement
nothing in **OUT OF SCOPE**. If something seems missing, it goes in
[`docs/BACKLOG.md`](docs/BACKLOG.md), not into the code.

## IN SCOPE — the complete v1 deliverable list

1. Canonical event schema (`loopcanary/schema.py`)
2. Detector protocol with cascade support (`loopcanary/protocol.py`)
3. Three deterministic detectors (`loopcanary/detectors/`)
4. In-process Python API adapter (`loopcanary/api.py`) — primary interface
5. Claude Code transcript adapter (`loopcanary/adapters/claude_code.py`)
6. Validation script against a labeled trajectory dataset (`scripts/validate_trace.py`)
7. Demo examples (`examples/`)
8. README + SCOPE.md + BACKLOG.md
9. Tests (pytest), typing (`py.typed`), lint (ruff), GitHub Actions CI, packaging (pyproject.toml)

## OUT OF SCOPE — do not build, do not scaffold, do not "prepare for"

- Dashboard/UI/web anything; any server or backend; any network I/O in core
- LLM-judge detector (the protocol must support it as a third-party
  implementation; we do not implement it)
- Entropy/logprob/distributional detectors (v1.1 — schema carries the
  optional field, detectors do not exist yet)
- Adapters for Codex, LangGraph, AutoGen, OpenTelemetry ingestion
  (noted in `docs/BACKLOG.md` as `adapter-wanted`)
- Auto-intervention / loop-breaking / retry logic (signals only; the
  caller decides)
- Aggregate "trajectory health score" (TRACER-style) — we emit named,
  legible signals, not a composite number
- Any effectiveness/monitorability claims in docs ("signals improve task
  success" is future research, not a README sentence)
- Persistence layers, databases, config frameworks, plugin entry-point systems

## Why the freeze is the design

"Library, not platform" is the whole competitive position. The moment
loopcanary grows a backend, a dashboard, or a default LLM judge, it
re-enters the tracing-platform tier (Langfuse / MLflow / LangSmith /
Phoenix) and loses. Staying a cheap, local, in-process, deterministic
library is the only shape deployable inside a training rollout — and
that is the moat. The OUT list is enforced, not aspirational.
