"""Tests for the Claude Code transcript adapter.

These run against three hand-written fixtures under
``tests/fixtures/claude_code/`` that exercise the paths that matter for a
drift-prone, undocumented format: a well-formed session, a session with
malformed lines interleaved, and a session containing unknown record types.
The contract is: parse what you can, skip what you can't, never crash.
"""

from __future__ import annotations

from pathlib import Path

from loopcanary import Canary, Severity
from loopcanary.adapters.claude_code import ClaudeCodeSession

FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"


def _events(name: str):
    return list(ClaudeCodeSession(FIXTURES / name).events())


# ---------------------------------------------------------------------------
# well-formed
# ---------------------------------------------------------------------------


def test_well_formed_pairs_every_tool_use() -> None:
    events = _events("well_formed.jsonl")
    # 4 tool_use blocks, each with a matching tool_result -> 4 events.
    assert len(events) == 4
    assert [e.step for e in events] == [0, 1, 2, 3]
    assert events[0].action_type == "tool:Bash"
    assert events[3].action_type == "tool:Read"


def test_well_formed_identical_calls_share_action_fingerprint() -> None:
    events = _events("well_formed.jsonl")
    # first three are the same `python train.py --resume` Bash call.
    assert events[0].action_fingerprint == events[1].action_fingerprint
    assert events[1].action_fingerprint == events[2].action_fingerprint
    # the Read is a different action.
    assert events[3].action_fingerprint != events[0].action_fingerprint


def test_well_formed_identical_results_share_output_fingerprint() -> None:
    events = _events("well_formed.jsonl")
    # the three FileNotFoundError results are identical.
    assert events[0].output_fingerprint == events[1].output_fingerprint == events[2].output_fingerprint


def test_well_formed_drives_detectors_to_repeated_action_signal() -> None:
    canary = Canary()
    fired = []
    for event in ClaudeCodeSession(FIXTURES / "well_formed.jsonl").events():
        fired.extend(canary.observe(event))
    assert any(
        s.detector == "repeated_action" and s.severity is Severity.WARN for s in fired
    )


# ---------------------------------------------------------------------------
# malformed — must not crash, must skip bad lines
# ---------------------------------------------------------------------------


def test_malformed_skips_bad_lines_and_keeps_valid_pairs() -> None:
    events = _events("malformed.jsonl")
    # two valid tool_use/tool_result pairs survive; the non-JSON and the
    # broken-brace lines are skipped without raising.
    assert len(events) == 2
    assert all(e.action_type == "tool:Bash" for e in events)


# ---------------------------------------------------------------------------
# unknown record types — forward-compat: skip, don't choke
# ---------------------------------------------------------------------------


def test_unknown_types_are_skipped_but_real_tool_use_survives() -> None:
    events = _events("unknown_types.jsonl")
    # system / file-history-snapshot / weird_future_record_type / text-only
    # assistant are all skipped; only the Grep tool_use/result pair yields one.
    assert len(events) == 1
    assert events[0].action_type == "tool:Grep"


# ---------------------------------------------------------------------------
# unpaired / missing results
# ---------------------------------------------------------------------------


def test_unpaired_tool_use_yields_nothing(tmp_path: Path) -> None:
    # a tool_use with no matching tool_result must not emit a half-event.
    p = tmp_path / "unpaired.jsonl"
    p.write_text(
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"tool_use","id":"z1","name":"Bash","input":{"command":"ls"}}]}}\n',
        encoding="utf-8",
    )
    assert list(ClaudeCodeSession(p).events()) == []


def test_empty_file_yields_nothing(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert list(ClaudeCodeSession(p).events()) == []
