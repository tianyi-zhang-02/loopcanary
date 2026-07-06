"""Canonical event schema for loopcanary.

Everything a detector sees is a :class:`LoopEvent` — a small, frozen,
hashable record of one step of an agent loop. Adapters (in-process API,
Claude Code transcript, …) translate their native format into this shape;
detectors only ever see :class:`LoopEvent`, never the native format.

The design goal is *cheap*: this record must be constructable in
microseconds and light on allocation, because it is created once per step
inside loops that may run at rollout scale (thousands of short loops per
training batch). It is stdlib-only and carries no behaviour beyond being a
value.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = ["ModelSignals", "LoopEvent", "fingerprint"]


@dataclass(frozen=True)
class ModelSignals:
    """Optional model-internal signals attached to an event.

    Carried by the schema so it does not have to break in v1.1, but **v1
    detectors must not read these fields**. A future distributional
    detector (output-entropy collapse, logprob anomalies) will consume
    them; until then they exist only so adapters that *can* populate them
    (local/open models with logprob access) lose nothing.
    """

    mean_logprob: float | None = None
    entropy: float | None = None


@dataclass(frozen=True)
class LoopEvent:
    """One step of an agent loop, in canonical form.

    Attributes
    ----------
    step:
        Monotonically increasing index within a single run.
    action_type:
        Coarse kind of action, e.g. ``"tool_call"``, ``"message"``,
        ``"code_edit"``, or ``"tool:bash"`` from an adapter.
    action_fingerprint:
        Stable hash of the action's *semantic* content (see
        :func:`fingerprint`). Two steps that take the same action produce
        the same fingerprint — this is what ``repeated_action`` keys on.
    output_fingerprint:
        Stable hash of the observation / result the action produced. Novel
        outputs produce novel fingerprints — this is what ``null_progress``
        keys on.
    tokens_in_context:
        Best-effort context size in tokens; ``None`` when the adapter can't
        derive it. ``context_pressure`` self-disables gracefully on ``None``.
    timestamp:
        Wall-clock ``time.time()`` at construction.
    model_signals:
        Optional :class:`ModelSignals`; carried, never consumed in v1.
    metadata:
        Adapter-specific string extras. Not interpreted by core detectors.
    """

    step: int
    action_type: str
    action_fingerprint: str
    output_fingerprint: str
    tokens_in_context: int | None = None
    timestamp: float = field(default_factory=time.time)
    model_signals: ModelSignals | None = None
    metadata: Mapping[str, str] | None = None


def fingerprint(
    payload: str | bytes | Mapping[str, object],
    *,
    volatile: frozenset[str] = frozenset(),
) -> str:
    """Stable content hash: canonical-JSON → sha256 → first 16 hex chars.

    The result is deterministic and stable across processes and Python
    runs (unlike ``hash()``), so the same semantic action always yields the
    same fingerprint.

    Normalization rules:

    * ``str`` is hashed as its UTF-8 bytes.
    * ``bytes`` is hashed directly.
    * A ``Mapping`` is serialized to canonical JSON with **sorted keys** and
      compact separators, so key order never changes the hash. Any keys
      named in ``volatile`` are dropped before hashing — use this to strip
      caller-marked fields that change every run (timestamps, request ids,
      nonces) so they don't defeat repeated-action detection. Values that
      are not natively JSON-serializable fall back to ``str(value)``.

    16 hex chars = 64 bits of sha256, ample to avoid collision within a
    single run while keeping events small.
    """
    if isinstance(payload, bytes):
        data = payload
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    elif isinstance(payload, Mapping):
        cleaned = {k: v for k, v in payload.items() if k not in volatile}
        data = json.dumps(
            cleaned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    else:  # pragma: no cover - defensive; keeps the host from crashing
        data = str(payload).encode("utf-8")

    return hashlib.sha256(data).hexdigest()[:16]
