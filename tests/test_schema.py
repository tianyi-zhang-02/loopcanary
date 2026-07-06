"""Tests for the event schema and the fingerprint helper."""

from __future__ import annotations

import dataclasses

import pytest

from loopcanary.schema import LoopEvent, ModelSignals, fingerprint

# ---------------------------------------------------------------------------
# fingerprint stability
# ---------------------------------------------------------------------------


def test_fingerprint_is_16_hex_chars() -> None:
    fp = fingerprint("hello")
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_deterministic_for_str() -> None:
    assert fingerprint("bash: ls -la") == fingerprint("bash: ls -la")
    assert fingerprint("a") != fingerprint("b")


def test_fingerprint_bytes_and_str_of_same_content_match() -> None:
    assert fingerprint("x") == fingerprint(b"x")


def test_fingerprint_mapping_key_order_invariant() -> None:
    a = fingerprint({"tool": "bash", "cmd": "ls"})
    b = fingerprint({"cmd": "ls", "tool": "bash"})
    assert a == b


def test_fingerprint_mapping_value_sensitive() -> None:
    assert fingerprint({"cmd": "ls"}) != fingerprint({"cmd": "pwd"})


def test_fingerprint_strips_volatile_fields() -> None:
    base = {"tool": "bash", "cmd": "ls", "request_id": "abc"}
    other = {"tool": "bash", "cmd": "ls", "request_id": "xyz"}
    # Without stripping, the differing request_id changes the hash.
    assert fingerprint(base) != fingerprint(other)
    # With request_id marked volatile, the two collapse to the same hash.
    assert fingerprint(base, volatile=frozenset({"request_id"})) == fingerprint(
        other, volatile=frozenset({"request_id"})
    )


def test_fingerprint_handles_nested_and_nonjson_values() -> None:
    # Should not raise on nested structures or non-JSON-native values.
    fp = fingerprint({"a": [1, 2, {"b": 3}], "obj": object()})
    assert len(fp) == 16


# ---------------------------------------------------------------------------
# LoopEvent / ModelSignals
# ---------------------------------------------------------------------------


def test_loop_event_is_frozen_and_hashable() -> None:
    e = LoopEvent(
        step=0,
        action_type="tool:bash",
        action_fingerprint=fingerprint("ls"),
        output_fingerprint=fingerprint("a.py b.py"),
    )
    # frozen -> hashable
    assert hash(e) == hash(e)
    # frozen -> immutable
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.step = 1  # type: ignore[misc]


def test_loop_event_defaults() -> None:
    e = LoopEvent(
        step=3,
        action_type="message",
        action_fingerprint="deadbeefdeadbeef",
        output_fingerprint="cafecafecafecafe",
    )
    assert e.tokens_in_context is None
    assert e.model_signals is None
    assert e.metadata is None
    assert isinstance(e.timestamp, float)


def test_model_signals_carried_optional() -> None:
    ms = ModelSignals(mean_logprob=-0.4, entropy=1.2)
    e = LoopEvent(
        step=0,
        action_type="message",
        action_fingerprint="a" * 16,
        output_fingerprint="b" * 16,
        model_signals=ms,
    )
    assert e.model_signals is ms
    assert e.model_signals.mean_logprob == -0.4
