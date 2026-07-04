"""Reporting and integrity-adjusted leaderboards.

The reporting layer consumes per-trajectory
:class:`~loopcanary.core.verdict.AuditVerdict` records and produces the
artifacts users actually look at:

* :mod:`loopcanary.reporting.leaderboard` — aggregate verdicts into an
  integrity-adjusted leaderboard plus the ``compare`` rank-diff report.
* :mod:`loopcanary.reporting.exporters` — JSON, Markdown, CSV exporters.
"""

from __future__ import annotations
