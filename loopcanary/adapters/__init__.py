"""Adapters that map external agent traces onto canonical loopcanary events.

Each adapter reads some foreign trace format and yields
:class:`loopcanary.schema.LoopEvent` objects. Adapters are the only place
foreign-format assumptions live; the core detectors never see raw traces.

Shipped in v1:

- :mod:`loopcanary.adapters.claude_code` — Claude Code JSONL transcripts.

Wanted (see ``docs/BACKLOG.md``): Codex, LangGraph, AutoGen, OpenTelemetry.
"""
