# Decisions

Ambiguities resolved during the v1.0 build. Per the brief: when an
instruction is ambiguous, choose the simpler interpretation, record it
here, and continue.

- **Fresh stdlib design supersedes the pydantic seed.** The repo
  previously held a pydantic `TrajectoryEvent` / `SemanticVerdict` data
  model (the pre-pivot batch shape and its stripped SDK seed). The brief
  specifies a *stdlib-only* core with a new `LoopEvent` dataclass and a
  flat `loopcanary/` layout. This build removes the pydantic seed and the
  strip-era SDK docs and lays down the brief's structure from scratch. It
  supersedes the earlier "strip to SDK seed" PR.

- **Flat layout, not `src/`.** The brief's tree shows a flat
  `loopcanary/` package at the repo root. Followed verbatim (was
  `src/loopcanary/`). Simpler and matches the spec.

- **License changed MIT → Apache-2.0** per the brief's repo-standards
  section.

- **Python floor 3.10** (brief says ≥3.10). Consequence: no `enum.StrEnum`
  (3.11+). `Severity` is a plain `enum.Enum` with ordered integer values
  so severities compare/escalate. `X | Y` annotations are fine under
  `from __future__ import annotations`.

- **mypy is best-effort, not a CI gate.** The brief says "mypy-clean or
  py.typed best-effort." CI runs mypy but does not fail on it (`|| true`);
  ruff + pytest are the gates. `py.typed` ships.

- **`fingerprint` volatile-field stripping is opt-in via a marker.** The
  brief says "strip volatile fields the caller marks." Implemented as:
  `fingerprint(payload, volatile=frozenset(...))` drops those keys from a
  Mapping before hashing. Callers that don't pass `volatile` get the full
  payload hashed. Documented in the function docstring.

- **`context_pressure` "no accompanying change in output diversity".** The
  brief couples the growth-rate trigger to output-fingerprint diversity.
  Implemented as: the rate trigger fires only when the distinct
  `output_fingerprint` count over the same window is ≤ a small constant
  (default 2) — i.e., context is ballooning while output isn't changing.
  The absolute-threshold trigger is independent of diversity.

- **`summary()` returns per-detector signal counts by severity.** The
  brief says "per-detector counts." Returns
  `{detector_name: {"INFO": n, "WARN": n, "ALERT": n, "total": n}}`.

- **Claude Code adapter emits one event per tool_use, at result time.** The
  transcript pairs an assistant `tool_use` with a later user `tool_result`
  by `tool_use_id`; the event is emitted when the result arrives, so both
  action and output fingerprints are populated. An unpaired `tool_use`
  (no matching result yet) emits nothing rather than a half-event. All
  format assumptions live in `_parse_record` + the pairing loop; unknown
  record types and malformed lines are skipped, never fatal. Transcript
  mode is **as-written (near-real-time), not pre-step** — noted in the
  module docstring so no one mistakes it for an in-loop hook.
