"""Claude Code transcript adapter.

Claude Code writes JSONL session transcripts (under
``~/.claude/projects/<project-slug>/*.jsonl``). This adapter reads such a
transcript and yields canonical :class:`~loopcanary.schema.LoopEvent`
objects — one per ``tool_use`` block, paired with its matching
``tool_result`` — so the deterministic detectors can run over a real
Claude Code session.

Honest caveat: **transcript mode detects as-written (near-real-time),
not pre-step.** loopcanary sees a tool call once it has been written to the
transcript, not before it runs. The in-process API
(:class:`loopcanary.Canary`) is where pre-step callbacks are real; this
adapter is for watching a session (or a finished transcript) from outside
the Claude Code process.

The transcript format is undocumented and may drift. Everything this
adapter assumes about it is confined to :func:`_parse_record` and the
pairing logic in :meth:`ClaudeCodeSession.events`; unknown record types and
malformed lines are skipped, never fatal. If the real format diverges from
these assumptions at runtime, the adapter degrades to yielding fewer events
rather than crashing the host.

CLI::

    python -m loopcanary.adapters.claude_code --watch <transcript.jsonl>
    python -m loopcanary.adapters.claude_code --watch <transcript.jsonl> --follow
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Iterator, Mapping
from pathlib import Path

from loopcanary.schema import LoopEvent, fingerprint

__all__ = ["ClaudeCodeSession"]

_log = logging.getLogger("loopcanary.adapters.claude_code")


def _parse_record(line: str) -> dict | None:
    """Parse one transcript line into a record dict, or ``None`` to skip.

    This is the single place the (undocumented) transcript format is
    assumed. A line that isn't a JSON object is skipped with a debug log —
    never raised — so a malformed or partially-written line can't crash a
    host that is tailing a live session.
    """
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        _log.debug("skipping non-JSON transcript line: %.60r", line)
        return None
    if not isinstance(obj, dict):
        _log.debug("skipping non-object transcript record: %.60r", line)
        return None
    return obj


def _content_blocks(record: dict) -> list[dict]:
    """Return the list of content blocks in a record's message, defensively.

    ``message.content`` may be a list of blocks, a bare string (plain text
    turn), or absent. Only list-of-dict blocks carry tool_use / tool_result.
    """
    message = record.get("message")
    if not isinstance(message, Mapping):
        return []
    content = message.get("content")
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _stringify(value: object) -> str:
    """Best-effort stringify of tool_result content (string or block list)."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for b in value:
            if isinstance(b, Mapping) and "text" in b:
                parts.append(str(b["text"]))
            else:
                parts.append(str(b))
        return "\n".join(parts)
    return str(value)


class ClaudeCodeSession:
    """A Claude Code JSONL transcript, as a stream of canonical events."""

    def __init__(self, path: str | Path, *, poll_interval: float = 0.5) -> None:
        self.path = Path(path)
        self.poll_interval = poll_interval

    def events(self, *, follow: bool = False) -> Iterator[LoopEvent]:
        """Yield one :class:`LoopEvent` per tool_use, paired with its result.

        Assistant ``tool_use`` blocks are buffered by id; when the matching
        ``tool_result`` arrives (in a later user record) the pair is emitted
        as one event. Steps increment per emitted event.

        With ``follow=True`` the file is tailed (polling every
        ``poll_interval`` seconds) and events are yielded as the session
        writes them; the generator runs until the caller stops consuming.
        """
        pending: dict[str, dict[str, object]] = {}
        step = 0
        for record in self._read_records(follow=follow):
            rtype = record.get("type")
            if rtype == "assistant":
                for block in _content_blocks(record):
                    if block.get("type") == "tool_use":
                        tid = block.get("id")
                        if isinstance(tid, str):
                            pending[tid] = {
                                "name": block.get("name", "unknown"),
                                "input": block.get("input", {}),
                            }
            elif rtype == "user":
                for block in _content_blocks(record):
                    if block.get("type") != "tool_result":
                        continue
                    tid = block.get("tool_use_id")
                    if not isinstance(tid, str) or tid not in pending:
                        continue
                    call = pending.pop(tid)
                    name = str(call["name"])
                    yield LoopEvent(
                        step=step,
                        action_type=f"tool:{name}",
                        action_fingerprint=fingerprint(
                            {"tool": name, "input": call["input"]}
                        ),
                        output_fingerprint=fingerprint(
                            _stringify(block.get("content", ""))
                        ),
                        tokens_in_context=None,
                        metadata={"tool": name},
                    )
                    step += 1
            # any other record type is skipped by design

    def _read_records(self, *, follow: bool) -> Iterator[dict]:
        """Yield parsed record dicts from the transcript (optionally tailing)."""
        if not follow:
            with self.path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    rec = _parse_record(line)
                    if rec is not None:
                        yield rec
            return

        # follow mode: read what's there, then poll for appended lines.
        with self.path.open("r", encoding="utf-8", errors="replace") as fh:
            while True:
                line = fh.readline()
                if line:
                    rec = _parse_record(line)
                    if rec is not None:
                        yield rec
                else:
                    time.sleep(self.poll_interval)


def main(argv: list[str] | None = None) -> int:
    """CLI: stream signals from a Claude Code transcript to stderr."""
    parser = argparse.ArgumentParser(
        prog="python -m loopcanary.adapters.claude_code",
        description="Watch a Claude Code transcript and print loopcanary signals.",
    )
    parser.add_argument("--watch", required=True, metavar="TRANSCRIPT.jsonl",
                        help="path to a Claude Code JSONL transcript")
    parser.add_argument("--follow", action="store_true",
                        help="tail the file as the session runs (default: process once)")
    args = parser.parse_args(argv)

    # Imported here so the adapter module stays importable without the API.
    from loopcanary.api import Canary

    canary = Canary(
        on_signal=lambda s: print(
            f"[{s.severity.name}] {s.detector}: {s.message}", file=sys.stderr
        )
    )
    session = ClaudeCodeSession(args.watch)
    try:
        for event in session.events(follow=args.follow):
            canary.observe(event)
    except KeyboardInterrupt:  # pragma: no cover - interactive follow mode
        pass

    print("\nsummary:", file=sys.stderr)
    for detector, counts in canary.summary().items():
        print(f"  {detector}: {counts}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
