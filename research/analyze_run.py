"""Reproduce the transformation-degradation analysis from a committed run.

Usage:
    python research/analyze_run.py [path-to-run.json] [n_bootstrap]

Default path is the committed Sonnet-4-6 n=60 run. Reuses
``loopcanary.report.compute_report`` so the AUROC / bootstrap-CI / Δ
numbers regenerate from the raw per-trajectory records, rather than
trusting the ``report`` block stored inside the run file. This is the
reproducibility path for the SaTML finding: point it at any run JSON,
optionally bump the bootstrap resample count, and get the table back.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopcanary.report import ScoreRecord, compute_report

_DEFAULT_RUN = "research/data/sonnet-4-6_n60_20260608.json"


def load_records(path: str) -> tuple[str | None, list[ScoreRecord]]:
    payload = json.loads(Path(path).read_text())
    records = [
        ScoreRecord(
            trajectory_id=r["trajectory_id"],
            transformation_name=r["transformation_name"],
            ground_truth_label=r["ground_truth_label"],
            monitor_score=r["monitor_score"],
            abstain=r["abstain"],
        )
        for r in payload["records"]
    ]
    return payload.get("model"), records


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_RUN
    n_boot = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    model, records = load_records(path)
    report = compute_report(records, n_bootstrap=n_boot)
    print(f"run:   {path}")
    print(f"model: {model}   records: {len(records)}   n_bootstrap: {n_boot}\n")
    report.render()


if __name__ == "__main__":
    main()
