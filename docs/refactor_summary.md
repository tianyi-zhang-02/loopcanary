# Refactor summary — post-audit hardening

Date: 2026-05-25. Branch: `main`. Four commits, atomic per task.

This refactor addresses the four findings from `docs/repo_audit.md` that
needed code-level fixes before the project repositions toward post-hoc
monitor evaluation. Scope was held tight: no new features, no Phase 1
work, no SWE-bench-adapter changes, no MALT ingestion.

## What changed

| Commit | Files | Lines |
|---|---|---|
| `refactor(core): unify Trajectory event stream` | `core/events.py` (new), `core/trajectory.py`, `tests/core/test_events.py` (new) | +285 / −10 |
| `feat(verdict): add abstain field and band validator` | `core/verdict.py`, `tests/core/test_verdict.py` (new) | +183 / −5 |
| `chore(deps): move llm and sandbox deps to extras` | `pyproject.toml`, `README.md`, `uv.lock` | +24 / −10 |
| `docs(runner): mark AuditRunner as Phase 0 scaffold` | `core/runner.py` | +20 / −2 |

Test count: 1 → 18 (1 smoke + 6 event-stream + 11 verdict). All green.
`ruff check .` and `mypy src/monitorstress` both clean on every commit.

## Public API delta

- **`Trajectory.events: list[TrajectoryEvent]`** replaces the parallel
  `steps` / `file_edits` / `shell_commands` lists.
  `TrajectoryEvent` is a Pydantic-tagged discriminated union of
  `ReasoningEvent | ToolCallEvent | ObservationEvent | ScoringEvent`,
  discriminator field `event_type`. New convenience iterators:
  `tool_calls()`, `observations()`, `reasoning()`, `paired_calls()`.
- **`SemanticVerdict.abstain: bool`** added (default `False`). A
  `@model_validator(mode="after")` enforces three invariants together:
  `0.0 ≤ lo ≤ hi ≤ 1.0`, `abstain=True ⇔ verdict == ABSTAIN`,
  `abstain=True ⇒ confidence_band == (0.0, 1.0)`.
- **`TaxonomyTag`** (new `StrEnum`) replaces `taxonomy_tags: list[str]`.
  13 values: 11 MALT-derived behavioural categories plus `other` and
  `normal`. Pydantic auto-coerces string inputs and rejects unknowns.
- **`StepType`, `Step`, `FileEdit`, `ShellCommand`** kept in
  `core/trajectory.py` with `.. deprecated::` notes. One release cycle
  of soft deprecation.
- **`anthropic`, `openai`, `docker`** moved out of
  `[project.dependencies]` into `[project.optional-dependencies]`
  under `llm` and `sandbox` extras. Default install is now Pydantic +
  Typer only.

## Migration path

There are no external consumers of the old three-list `Trajectory`.
Nothing inside the repo read `.steps`, `.file_edits`, or
`.shell_commands`; the audit confirmed this and the post-refactor
grep confirmed it again. For internal future code, the migration
pattern is:

```python
# OLD (deprecated, still importable)
traj = Trajectory(
    trajectory_id="t",
    benchmark="b",
    task_id="x",
    steps=[Step(index=0, type=StepType.THOUGHT, content="…")],
    shell_commands=[ShellCommand(command="ls")],
)

# NEW
traj = Trajectory(
    trajectory_id="t",
    benchmark="b",
    task_id="x",
    events=[
        ReasoningEvent(content="…"),
        ToolCallEvent(tool_name="shell", arguments={"cmd": "ls"}, call_id="c1"),
        ObservationEvent(content="<output>", source="stdout", call_id="c1"),
    ],
)
```

`call_id` is optional but recommended — it's what `paired_calls()`
uses to join calls to observations.

## Judgment calls made

A few choices were judgment calls, not bug fixes; they're recorded
here so they can be revisited.

1. **`SemanticLabel.ABSTAIN` was already an enum value.** The audit
   said "abstention may not be a first-class field"; on inspection it
   was a first-class *label* but not a first-class *flag*. The new
   `abstain: bool` is the canonical signal for calibration code that
   wants to branch without inspecting the label; the validator
   enforces strict biconditional consistency with the label so the
   two can never drift.
2. **`TaxonomyTag` doesn't exist yet — created it.** The audit said
   `taxonomy_tags` was a list of untyped strings and recommended an
   enum. The new enum uses the 11 MALT categories you listed plus
   `other` and `normal`. This isn't a commitment to MALT — the enum
   is open to extension and `other` is the explicit catch-all.
3. **`ToolCallEvent.arguments` has no default.** Followed the spec
   literally; passing `arguments={}` is the explicit way to encode
   an argless tool call.
4. **`HarnessResult` retained alongside `ScoringEvent`.** The spec
   said "events list replaces the three lists, nothing else changes
   at the Trajectory level," so the existing top-level
   `harness_result` field stays. There's some semantic overlap with
   in-stream `ScoringEvent`s — flagged in `followups.md`.
5. **`docs/pivot_review.md` was referenced but doesn't exist.** The
   inline context in the prompt (option D, METR/EvilGenie/Meerkat
   operate on interleaved sequences) was sufficient. Flagged so it
   can be written when convenient.

## Out of scope — see `docs/followups.md`

Items I noticed during the refactor that weren't in the four-task
scope have been recorded in `docs/followups.md` per the scope-discipline
note. No questions ended up in `docs/refactor_questions.md`; everything
resolved cleanly during implementation.
