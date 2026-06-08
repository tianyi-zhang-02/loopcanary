# monitorstress — Repo Audit

Produced: 2026-05-25. Git HEAD: `39795a5`. No code was written, refactored, or tested as part
of this audit; everything below is a read-only snapshot.

---

## 1. Directory tree (3 levels)

```
monitorstress/
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── docs/
│   ├── architecture.md
│   ├── exploit-taxonomy.md
│   └── related-work.md
├── examples/
│   └── README.md                   # placeholder only
├── pyproject.toml
├── src/
│   └── monitorstress/
│       ├── __init__.py             # __version__ = "0.0.1"
│       ├── benchmarks/
│       │   ├── base.py             # BenchmarkAdapter ABC + @register
│       │   ├── swe_bench.py        # SWEBenchAdapter stub
│       │   └── terminal_bench.py   # TerminalBenchAdapter stub
│       ├── cli.py                  # typer app: run / leaderboard / compare
│       ├── core/
│       │   ├── runner.py           # AuditConfig + AuditRunner stubs
│       │   ├── trajectory.py       # Trajectory model
│       │   └── verdict.py          # Finding/Verdict/AuditVerdict schemas
│       ├── layer1_workspace/
│       │   ├── fs_differ.py        # FSDiffer + PathClass
│       │   ├── process_tracer.py   # ProcessTracer stub
│       │   └── sandbox.py          # DockerSandbox stub
│       ├── layer2_syntactic/
│       │   ├── ast_scanner.py      # ASTScanner stub
│       │   ├── code_extractor.py   # CodeEdit + extract_code_from_trajectory stub
│       │   └── exploit_signatures.py  # ExploitSignature + 5 stubs; get_all_signatures → []
│       ├── layer3_semantic/
│       │   ├── escalation.py       # EscalationPolicy stub
│       │   ├── judge.py            # SemanticJudge stub
│       │   ├── prompts.py          # JUDGE_PROMPT_TEMPLATE = ""
│       │   └── providers/
│       │       ├── base.py         # LLMProvider ABC
│       │       ├── anthropic_provider.py  # stub
│       │       ├── openai_provider.py     # stub
│       │       └── vllm_provider.py       # stub
│       └── reporting/
│           ├── exporters.py        # JSON/Markdown/CSV exporter stubs
│           └── leaderboard.py      # IntegrityLeaderboard + ComparisonReport stubs
└── tests/
    ├── core/                       # __init__.py only
    ├── layer1/                     # __init__.py only
    ├── layer2/                     # __init__.py only
    ├── layer3/                     # __init__.py only
    └── test_smoke.py               # 1 test
```

Total tracked Python source files: 27. Docs: 5 (architecture, exploit-taxonomy, related-work,
examples/README, this file). Tests: 1 real test + 4 empty subdirectory inits.

---

## 2. Phase 0 plan vs. reality

README Phase 0 claims: _"Package skeleton, CI, docs, stub modules, verdict schemas as public
API."_ Verification by file/line:

| Claim | Evidence | Status |
|---|---|---|
| Package skeleton | `src/monitorstress/__init__.py` exposes `__version__` | ✅ |
| CI | `.github/workflows/ci.yml` — lint + mypy + pytest | ✅ |
| Docs | `docs/architecture.md`, `exploit-taxonomy.md`, `related-work.md` | ✅ |
| Stub modules — Layer 1 | `sandbox.py`, `fs_differ.py`, `process_tracer.py` — all raise `NotImplementedError` | ✅ |
| Stub modules — Layer 2 | `ast_scanner.py`, `exploit_signatures.py` — 5 `_match_*` stubs; `get_all_signatures() → []` | ✅ |
| Stub modules — Layer 3 | `judge.py`, `escalation.py`, `prompts.py`, 3 provider stubs | ✅ |
| Verdict schemas as public API | `core/verdict.py` fully typed; re-exported from `__init__.py` via `__all__` | ✅ |
| CLI surface | `cli.py` — `run`, `leaderboard`, `compare` all raise `NotImplementedError` | ✅ |
| Reporting surface | `leaderboard.py`, `exporters.py` — all raise `NotImplementedError` | ✅ |

One honest nuance: the `AuditRunner` in `runner.py` is in Phase 0 but lives in `core/`, which
the README places in Phase 1 scope. In practice it's a 15-line `@dataclass` config + class
shell with two `NotImplementedError` stubs — comfortably scaffold-level.

---

## 3. Public type definitions (verbatim + analysis)

### `Step` (`core/trajectory.py`, lines 61–68)

```python
class Step(BaseModel):
    index: int = Field(..., description="Zero-based index in the trajectory.")
    type: StepType
    timestamp: datetime | None = None
    content: str = Field(..., description="Free-form textual content of the step.")
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Analysis.** `content` is a single free-form string — it's intentionally agnostic to whether
the step is a tool call, shell command, or thought. Structured fields for shell commands and
file edits live at the `Trajectory` level (`shell_commands`, `file_edits`), so `Step` only
carries the narrative. The open `metadata` dict is the right escape hatch for now, though Phase 1
will need to decide whether benchmark-specific fields go there or into a subclass.

---

### `Trajectory` (`core/trajectory.py`, lines 81–109)

```python
class Trajectory(BaseModel):
    trajectory_id: str
    benchmark: str
    task_id: str
    agent_id: str | None = None

    steps: list[Step] = Field(default_factory=list)
    file_edits: list[FileEdit] = Field(default_factory=list)
    shell_commands: list[ShellCommand] = Field(default_factory=list)
    harness_result: HarnessResult | None = None

    workspace_root: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dir(cls, path: Path) -> Trajectory:
        raise NotImplementedError("Phase 1: dispatch to benchmark adapter from manifest.")
```

**Analysis.** Three parallel lists (`steps`, `file_edits`, `shell_commands`) rather than a
single polymorphic event stream is a deliberate trade-off: it makes Layer 1 and Layer 2
consumers cheap to write (they only pull what they need) but loses cross-list temporal ordering.
Phase 1 will need to decide whether timestamps on `Step` are sufficient to reconstruct order or
whether a sequence index is needed across all three lists. `workspace_root` being optional is
correct for Phase 0; Layer 1 will make it required at runtime.

---

### `SemanticVerdict` (`core/verdict.py`, lines 126–167)

```python
class SemanticVerdict(BaseModel):
    verdict: SemanticLabel
    confidence_band: tuple[float, float] = Field(
        ..., description="Closed [low, high] confidence interval in [0, 1]."
    )
    reasoning: str
    escalated: bool = False
    escalated_from: str | None = None
    taxonomy_tags: list[str] = Field(default_factory=list)

    @property
    def band_width(self) -> float:
        lo, hi = self.confidence_band
        return hi - lo
```

**Analysis.** `confidence_band` as a tuple rather than two separate fields is clean but has a
known Pydantic v2 validation gap: no field-level validator enforces `lo ≤ hi` or that both are
in `[0, 1]`. Phase 4 should add a `@model_validator` before the judge produces live output or
the escalation policy reads `band_width`. The `taxonomy_tags` list is untyped strings today;
switching to a `TaxonomyTag` StrEnum in Phase 4 will catch misspellings from the judge without
extra runtime code.

---

### `AuditVerdict` (`core/verdict.py`, lines 175–232)

```python
class AuditVerdict(BaseModel):
    trajectory_id: str
    benchmark: str
    task_id: str
    agent_id: str | None = None

    layer1_findings: list[WorkspaceFinding] = Field(default_factory=list)
    layer2_findings: list[SyntacticFinding] = Field(default_factory=list)
    layer3_verdict: SemanticVerdict | None = None

    integrity_label: IntegrityLabel
    rationale: str

    harness_passed: bool | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def compose(cls, *, trajectory_id, benchmark, task_id, agent_id,
                harness_passed, layer1_findings, layer2_findings,
                layer3_verdict) -> AuditVerdict:
        raise NotImplementedError("Phase 5: implement composition policy.")
```

**Analysis.** The schema is production-ready for downstream consumers: the three per-layer
fields are independently nullable/empty, `integrity_label` is always present, and `uncertain`
is a valid label so callers don't need to handle `None`. The composition policy living on the
class (`compose`) is the right call — it keeps the schema and the logic co-located. The one
risk: `integrity_label` is a required field with no default, so callers constructing a verdict
directly (e.g., in tests) must provide it explicitly. That's intentional, not a bug.

---

## 4. Anything beyond Phase 0

**Commits:** 2 on `main`. No other branches.

```
39795a5  docs: switch security reporting to GitHub PVR
c21b0d3  chore: scaffold monitorstress project structure
```

**Branches:** `main` only. No `dev`, `phase1`, or experimental branches.

**Extra directories / files beyond the spec:** None. The four test subdirectories
(`tests/core/`, `tests/layer1/`, `tests/layer2/`, `tests/layer3/`) contain only `__init__.py`
markers — they were scaffolded deliberately so pytest discovers them without configuration
changes when implementations land.

**CONTRIBUTING.md / LICENSE:** Both present and clean; not strictly "Phase 0" deliverables
per the roadmap but appropriate for a public repo and not surprising.

---

## 5. Dependencies

**Declared in `pyproject.toml`:**

| Package | Pinned range | Actually imported in `src/`? |
|---|---|---|
| `pydantic` | `>=2.6,<3` | Yes — `BaseModel`, `Field`, `ConfigDict` throughout |
| `typer` | `>=0.12,<1` | Yes — `cli.py` |
| `anthropic` | `>=0.40,<1` | No — `anthropic_provider.py` is a stub with no `import anthropic` |
| `openai` | `>=1.50,<3` | No — `openai_provider.py` is a stub with no `import openai` |
| `docker` | `>=7.1,<8` | No — `sandbox.py` is a stub with no `import docker` |

**Observation:** three of five runtime dependencies are phantom at this stage — installed but
never imported. That's fine for a Phase 0 scaffold that's declaring intent. It does mean
`uv sync` pulls `anthropic`, `openai`, and `docker` into the venv even though nothing calls
them yet. Worth noting when trimming install time in CI later.

**Stdlib only (no third-party):** `abc`, `ast`, `collections.abc`, `dataclasses`, `datetime`,
`enum`, `pathlib`, `typing`.

---

## 6. Tests

```
$ .venv/bin/python -m pytest --collect-only -q
tests/test_smoke.py::test_version_exposed
1 test collected in 0.00s
```

One test. It asserts `isinstance(monitorstress.__version__, str)` and that it's non-empty.

The four subdirectory inits (`tests/core/`, `tests/layer1/`, `tests/layer2/`, `tests/layer3/`)
contribute zero tests. They exist to define the layout for future phases.

Coverage this buys: package import doesn't explode, version string is present. That's it —
which is exactly right for Phase 0. Running `pytest -x` in CI on the current codebase is
green in under a second.

---

## 7. Pivot survival

### (a) Dropping or delaying the SWE-bench plan

The scaffold survives cleanly. `SWEBenchAdapter` in `benchmarks/swe_bench.py` is a stub
registered via `@register("swe-bench")`; no other file has a hard dependency on it. The
`Trajectory` schema is benchmark-agnostic — `benchmark: str` is a free-form field. If SWE-bench
data access turns out to be more friction than expected (license, environment reconstruction,
Docker image availability), the entire `swe_bench.py` file can be deleted or swapped without
touching `core/`, `layer1_workspace/`, or `layer2_syntactic/`. The risk is that Phase 1's
"survey OpenInference / Inspect AI / AgentOps" note may have been written with SWE-bench's
trace format in mind; a different benchmark may need a different survey scope.

### (b) MALT monitor pivot (post-hoc → real-time monitoring)

The scaffold does **not** survive this pivot without meaningful redesign. Every public-API
method (`audit`, `audit_many`, `from_dir`) takes a completed `Trajectory`. There is no
streaming, partial-trajectory, or event-driven entry point anywhere in the scaffold. The
`Step` model has a `timestamp` field that could support windowed analysis, but `Trajectory`
is built to be closed (a finished run), not open. If the project pivots toward monitoring
live agent loops — watching for exploit patterns mid-run and interrupting rather than labelling
after the fact — the `AuditRunner` needs to be redesigned as a stateful stream processor, and
`Layer 2`'s AST scanner would need to operate on partial file state. The verdict schema could
be reused for per-checkpoint snapshots, but the composition logic would be different. This is
a significant but not impossible refactor; the type definitions in `core/verdict.py` are the
most reusable piece.

### (c) Calibration-on-MALT pivot (using MALT traces to calibrate the LLM judge)

The scaffold handles this gracefully. Calibration requires: (1) a labeled set of trajectories,
(2) a way to run the judge over them and collect `SemanticVerdict` outputs, and (3) comparing
`confidence_band` against ground-truth labels. All three are structurally supported: `Trajectory`
can hold any benchmark's traces, `SemanticJudge.judge()` returns `SemanticVerdict` (once
implemented), and `SemanticVerdict.confidence_band` + `band_width` are already in the schema
precisely because calibration was in scope. The missing piece is a calibration harness — a
small script that loads a labeled MALT corpus, runs `AuditRunner` with Layer 3 only, and
plots calibration curves. That's a Phase 4 artifact, not a schema change. The current
`integrity_label` on `AuditVerdict` maps cleanly to a binary calibration target
(`exploit / uncertain / clean → positive / uncertain / negative`). No redesign needed; just
an implementation.
