# Contributing to monitorstress

Thanks for your interest. `monitorstress` is in the middle of a
substantial direction change — v0.1 batch prototype → v1.0
observability library — so the shape of "how to contribute" depends on
which piece you want to touch.

## Current status of the codebase

- **v0.1 batch CLI** — functional, on `main`, has 111 tests. Its docs
  are marked SUPERSEDED but the code still runs. Bug fixes are
  welcome; new *features* in the batch shape probably aren't the best
  use of contributor time.
- **v1.0 SDK** — designed but not yet implemented. The canonical spec
  is [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md); the
  implementation sequence is described in that doc's "Immediate next
  steps" section. The public API surface locks under semver at v1.0
  tag, so **API-shape feedback right now is more valuable than a
  premature implementation PR**.

## Where feedback is most useful today

1. **v1.0 API shape.** Read
   [`docs/pivot_v1_agentic.md`](docs/pivot_v1_agentic.md). Open an
   issue with concrete feedback on the `watch()` context manager
   signature, the `Detector` protocol, the initial detector set, or
   the run-output JSON schema. The four surfaces named in the plan
   doc's semver commitment are what needs to be right *before* code
   lands.
2. **Naming.** The plan doc reopens the rename question. Weigh in on
   the shortlist (`driftlens`, `looplens`, `agentgaze`, `agentscope`,
   `driftwatch`, or keep `monitorstress`) in an issue.
3. **Missing detectors or event types.** If there's a degradation
   pattern the initial detector set misses, or a memory/compression
   event type worth adding to the extended `TrajectoryEvent`
   variants, open an issue with a concrete example.

## Local development (v0.1 batch shape)

```bash
git clone https://github.com/tianyi-zhang-02/monitorstress
cd monitorstress
uv sync --all-extras
uv run pytest -q
uv run ruff check .
uv run mypy src/monitorstress
```

All three must pass. The CI matrix runs Python 3.11 and 3.12.

## Standing conventions

- **Never push to `main`.** Everything ships via PRs.
- **Never force-push.** Ever.
- **Never rewrite git history on pushed branches.**
- **Never commit secrets.** `.env` and `.env.*` are gitignored;
  never commit keys, tokens, or credentials.
- **Feature branches use short descriptive names** — `fix/…`, `feat/…`,
  `docs/…`, `chore/…`.
- **One commit per logical change.** PRs with a clean sequence of
  small commits are easier to review than one giant "do everything"
  commit.
- **All tests, lint, and types must pass** before opening a PR. CI
  will fail otherwise.

## Style

- **Python 3.11+.** Use modern syntax (`X | Y` unions, `dict[str, Any]`,
  etc.); `from __future__ import annotations` is on at every module
  where types are used.
- **Type hints on public API surfaces.** Anything callable from
  outside its module needs annotations. Private helpers can go
  without if it improves clarity.
- **Docstrings on `class` and public functions.** Explain *why*, not
  *what* — the reader can already read the code.
- **Tests: no live API calls.** All Anthropic calls are mocked via
  `unittest.mock`; MALT calls use committed fixtures under
  `tests/fixtures/`.

## Code of conduct

Be respectful. Assume good faith. If a reviewer's feedback stings,
sit with it for a day before responding.

## Questions

Open an issue with the `question` label, or start a
[GitHub Discussion](https://github.com/tianyi-zhang-02/monitorstress/discussions)
if the topic is broader than a specific piece of code.
