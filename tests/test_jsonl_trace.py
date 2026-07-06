"""Tests for the generic JSONL trace adapter."""

from __future__ import annotations

import json
from pathlib import Path

from loopcanary import Canary
from loopcanary.adapters import jsonl_trace as jt
from loopcanary.adapters.jsonl_trace import JsonlTrace, JsonlTraceFields


def _write(tmp_path: Path, rows: list[object | str]) -> Path:
    path = tmp_path / "trace.jsonl"
    lines = [row if isinstance(row, str) else json.dumps(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_jsonl_trace_maps_default_fields(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            {
                "step": 4,
                "action_type": "tool:bash",
                "action": {"cmd": "python train.py --resume"},
                "output": "FileNotFoundError",
                "tokens_in_context": 1234,
                "metadata": {"session_id": "s1", "step_kind": 7},
            }
        ],
    )

    events = list(JsonlTrace(path).events())

    assert len(events) == 1
    assert events[0].step == 4
    assert events[0].action_type == "tool:bash"
    assert events[0].tokens_in_context == 1234
    assert events[0].metadata == {"session_id": "s1", "step_kind": "7"}


def test_jsonl_trace_auto_numbers_missing_steps(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            {"action": "a", "output": "x"},
            {"action": "b", "output": "y"},
            {"step": 10, "action": "c", "output": "z"},
            {"action": "d", "output": "w"},
        ],
    )

    assert [event.step for event in JsonlTrace(path).events()] == [0, 1, 10, 11]


def test_jsonl_trace_skips_malformed_and_non_object_lines(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            "not json",
            ["not", "object"],
            {"action": "valid", "output": "ok"},
        ],
    )

    events = list(JsonlTrace(path).events())

    assert len(events) == 1
    assert events[0].step == 0


def test_jsonl_trace_uses_error_when_output_missing(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            {"action": "a", "error": "boom"},
            {"action": "a", "error": "boom"},
            {"action": "a", "error": "boom"},
        ],
    )

    canary = Canary()
    signals = []
    for event in JsonlTrace(path).events():
        signals.extend(canary.observe(event))

    assert any(signal.detector == "repeated_action" for signal in signals)


def test_jsonl_trace_custom_fields_and_volatile_keys(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            {
                "idx": 0,
                "kind": "handoff",
                "request": {"instruction": "fix tests", "request_id": "a"},
                "response": {"summary": "same failure", "timestamp": "t1"},
                "ctx": 100,
            },
            {
                "idx": 1,
                "kind": "handoff",
                "request": {"instruction": "fix tests", "request_id": "b"},
                "response": {"summary": "same failure", "timestamp": "t2"},
                "ctx": 120,
            },
        ],
    )
    fields = JsonlTraceFields(
        step="idx",
        action_type="kind",
        action="request",
        output="response",
        tokens="ctx",
    )

    events = list(
        JsonlTrace(
            path,
            fields=fields,
            action_volatile={"request_id"},
            output_volatile={"timestamp"},
        ).events()
    )

    assert events[0].action_type == "handoff"
    assert events[0].action_fingerprint == events[1].action_fingerprint
    assert events[0].output_fingerprint == events[1].output_fingerprint
    assert events[1].tokens_in_context == 120


def test_parse_record_rejects_non_object_json() -> None:
    assert jt._parse_record("[]") is None
    assert jt._parse_record("bad") is None
    assert jt._parse_record('{"action":"ok"}') == {"action": "ok"}
