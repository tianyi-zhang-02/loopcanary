"""Tests for the Claude Code transcript adapter.

These run against three hand-written fixtures under
``tests/fixtures/claude_code/`` that exercise the paths that matter for a
drift-prone, undocumented format: a well-formed session, a session with
malformed lines interleaved, and a session containing unknown record types.
The contract is: parse what you can, skip what you can't, never crash.
"""

from __future__ import annotations

import itertools
from pathlib import Path

from loopcanary import Canary, Severity
from loopcanary.adapters import claude_code as cc
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


# ---------------------------------------------------------------------------
# defensive helpers — the drift-tolerant parsing layer
# ---------------------------------------------------------------------------


def test_parse_record_rejects_non_object_json() -> None:
    # valid JSON that isn't an object (array, number, bare string) is skipped.
    assert cc._parse_record("[1, 2, 3]") is None
    assert cc._parse_record("42") is None
    assert cc._parse_record('"just a string"') is None
    assert cc._parse_record("   ") is None
    assert cc._parse_record('{"type":"system"}') == {"type": "system"}


def test_content_blocks_handles_string_and_missing_content() -> None:
    # message.content as a bare string (plain text turn) -> no blocks.
    assert cc._content_blocks({"message": {"content": "hello"}}) == []
    # no message key at all.
    assert cc._content_blocks({}) == []
    # message present but not a mapping.
    assert cc._content_blocks({"message": "nope"}) == []
    # list content keeps only dict blocks.
    blocks = cc._content_blocks({"message": {"content": [{"type": "text"}, "junk", 5]}})
    assert blocks == [{"type": "text"}]


def test_stringify_variants() -> None:
    assert cc._stringify("plain") == "plain"
    assert cc._stringify([{"text": "a"}, {"text": "b"}]) == "a\nb"
    assert cc._stringify([{"type": "image"}]) == "{'type': 'image'}"
    assert cc._stringify(42) == "42"


def test_tool_result_as_block_list_is_stringified(tmp_path: Path) -> None:
    # some transcripts put tool_result content as a list of text blocks.
    p = tmp_path / "blocklist.jsonl"
    p.write_text(
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"tool_use","id":"b1","name":"Bash","input":{"command":"ls"}}]}}\n'
        '{"type":"user","message":{"role":"user","content":'
        '[{"type":"tool_result","tool_use_id":"b1","content":[{"type":"text","text":"a.py"}]}]}}\n',
        encoding="utf-8",
    )
    events = list(ClaudeCodeSession(p).events())
    assert len(events) == 1
    assert events[0].action_type == "tool:Bash"


# ---------------------------------------------------------------------------
# follow mode + CLI
# ---------------------------------------------------------------------------


def test_follow_mode_reads_existing_lines_then_would_poll() -> None:
    # islice stops consuming after the 4 on-disk events, before the poll sleep.
    gen = ClaudeCodeSession(FIXTURES / "well_formed.jsonl", poll_interval=0.01).events(
        follow=True
    )
    events = list(itertools.islice(gen, 4))
    gen.close()
    assert len(events) == 4
    assert events[0].action_type == "tool:Bash"


def test_cli_main_processes_transcript(capsys) -> None:  # type: ignore[no-untyped-def]
    rc = cc.main(["--watch", str(FIXTURES / "well_formed.jsonl")])
    assert rc == 0
    err = capsys.readouterr().err
    # the repeated train.py call should surface a repeated_action signal + summary.
    assert "repeated_action" in err
    assert "summary:" in err
