"""Generic JSONL trace adapter.

This adapter is intentionally boring: one JSON object per line maps to one
canonical :class:`~loopcanary.schema.LoopEvent`. It is for teams that already
write simple step traces and want loopcanary signals before committing to a
framework-specific adapter.

Default line shape::

    {
      "step": 0,                         # optional; auto-numbered if absent
      "action_type": "tool:bash",        # optional; defaults to "action"
      "action": {"cmd": "python x.py"},  # required-ish; defaults to ""
      "output": "FileNotFoundError",     # optional; "error" is fallback
      "tokens_in_context": 1234,         # optional int/float
      "metadata": {"session_id": "s1"}   # optional string-ish mapping
    }

Malformed lines and non-object JSON values are skipped. Format assumptions
live here; detectors only see ``LoopEvent``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Mapping, Set
from dataclasses import dataclass
from pathlib import Path

from loopcanary.schema import LoopEvent, fingerprint

__all__ = ["JsonlTrace", "JsonlTraceFields"]

_log = logging.getLogger("loopcanary.adapters.jsonl_trace")


@dataclass(frozen=True)
class JsonlTraceFields:
    """Field names used to map JSONL records onto ``LoopEvent``."""

    step: str = "step"
    action_type: str = "action_type"
    action: str = "action"
    output: str = "output"
    error: str = "error"
    tokens: str = "tokens_in_context"
    metadata: str = "metadata"


def _parse_record(line: str) -> dict[str, object] | None:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        _log.debug("skipping non-JSON trace line: %.60r", line)
        return None
    if not isinstance(obj, dict):
        _log.debug("skipping non-object trace record: %.60r", line)
        return None
    return obj


def _metadata(value: object) -> Mapping[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    return {str(key): str(item) for key, item in value.items()}


def _tokens(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


class JsonlTrace:
    """A simple JSONL trace as a stream of canonical events."""

    def __init__(
        self,
        path: str | Path,
        *,
        fields: JsonlTraceFields | None = None,
        action_volatile: Set[str] = frozenset(),
        output_volatile: Set[str] = frozenset(),
    ) -> None:
        self.path = Path(path)
        self.fields = fields or JsonlTraceFields()
        self.action_volatile = action_volatile
        self.output_volatile = output_volatile

    def events(self) -> Iterator[LoopEvent]:
        """Yield one ``LoopEvent`` per parseable JSON object line."""
        auto_step = 0
        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                record = _parse_record(line)
                if record is None:
                    continue

                raw_step = record.get(self.fields.step)
                step = int(raw_step) if isinstance(raw_step, (int, float)) else auto_step
                auto_step = max(auto_step, step + 1)

                action = record.get(self.fields.action, "")
                output = record.get(self.fields.output, record.get(self.fields.error, ""))
                action_type = str(record.get(self.fields.action_type, "action"))

                yield LoopEvent(
                    step=step,
                    action_type=action_type,
                    action_fingerprint=fingerprint(action, volatile=self.action_volatile),  # type: ignore[arg-type]
                    output_fingerprint=fingerprint(output, volatile=self.output_volatile),  # type: ignore[arg-type]
                    tokens_in_context=_tokens(record.get(self.fields.tokens)),
                    metadata=_metadata(record.get(self.fields.metadata)),
                )
