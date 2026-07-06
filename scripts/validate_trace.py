#!/usr/bin/env python3
"""Validate loopcanary's deterministic detectors against a labeled trace set.

This script measures how well the deterministic detectors agree with
human/ground-truth labels on a dataset of agent trajectories — e.g. the
Patronus **TRACE** set, or any JSONL corpus with the shape assumed below.
It exists so the README's numbers come from a *reproducible run you can
point at a dataset*, not from an author's optimism.

    python scripts/validate_trace.py --dataset path/to/trace.jsonl
    python scripts/validate_trace.py --dataset path/to/trace.jsonl --detection lenient

**No results are hard-coded.** Until you run this against a real dataset,
the README carries `[to be filled by a validation run]` placeholders. Do
not paste numbers you have not produced with this script.

------------------------------------------------------------------------
Assumed dataset schema (the ONE place we pin trace-format assumptions)
------------------------------------------------------------------------
One JSON object per line. Each object is one trajectory::

    {
      "id": "traj-0001",
      "label": "degenerate",          # or "healthy"; see --positive-labels
      "steps": [
        {
          "action": "python train.py --resume",   # str | object
          "output": "FileNotFoundError ...",       # str | object
          "tokens_in_context": 5123,               # optional int
          "action_type": "tool:Bash"               # optional str
        },
        ...
      ]
    }

If the real dataset uses different field names, adjust `TRACE_FIELDS`
below — that constant and `iter_trajectories` are the only places the
external schema is assumed. Everything downstream speaks canonical
`LoopEvent`.

Ground truth is per-trajectory (does this trajectory contain a
loop-degradation the tool should catch?). We do not assume step-level
labels; the two detection definitions below bridge trajectory-level truth
and step-level firing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

# Make the package importable when run from a checkout without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loopcanary import Canary, LoopEvent, Signal, fingerprint  # noqa: E402
from loopcanary.detectors import default_detectors  # noqa: E402

# --- external-schema assumptions, pinned in one place ----------------------
TRACE_FIELDS = {
    "id": "id",
    "label": "label",
    "steps": "steps",
    "action": "action",
    "output": "output",
    "tokens": "tokens_in_context",
    "action_type": "action_type",
}
DEFAULT_POSITIVE_LABELS = frozenset({"degenerate", "stuck", "loop", "fail", "failure"})


@dataclass
class Trajectory:
    id: str
    is_positive: bool
    events: list[LoopEvent]


def _to_event(step: int, raw: Mapping[str, object]) -> LoopEvent:
    """Map one raw TRACE step onto a canonical LoopEvent."""
    action = raw.get(TRACE_FIELDS["action"], "")
    output = raw.get(TRACE_FIELDS["output"], "")
    tokens = raw.get(TRACE_FIELDS["tokens"])
    action_type = raw.get(TRACE_FIELDS["action_type"], "action")
    return LoopEvent(
        step=step,
        action_type=str(action_type),
        action_fingerprint=fingerprint(action),  # type: ignore[arg-type]
        output_fingerprint=fingerprint(output),  # type: ignore[arg-type]
        tokens_in_context=int(tokens) if isinstance(tokens, (int, float)) else None,
    )


def iter_trajectories(path: Path, positive_labels: frozenset[str]) -> Iterator[Trajectory]:
    """Yield trajectories from a JSONL dataset, skipping unparseable lines."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"warn: skipping non-JSON line {lineno}", file=sys.stderr)
                continue
            if not isinstance(obj, dict):
                continue
            steps = obj.get(TRACE_FIELDS["steps"], [])
            if not isinstance(steps, list):
                continue
            label = str(obj.get(TRACE_FIELDS["label"], "")).lower()
            events = [
                _to_event(i, s) for i, s in enumerate(steps) if isinstance(s, Mapping)
            ]
            yield Trajectory(
                id=str(obj.get(TRACE_FIELDS["id"], f"line-{lineno}")),
                is_positive=label in positive_labels,
                events=events,
            )


# --- detection definitions -------------------------------------------------
# Trajectory-level truth vs. step-level firing. We report both:
#   strict  — count a trajectory as "flagged" only if a detector fired at
#             ALERT severity (the tool's strongest claim). Fewer false
#             positives, may miss slow degradations.
#   lenient — count a trajectory as "flagged" if any signal of WARN or
#             above fired anywhere in it.
DETECTION_MODES = ("strict", "lenient")


def _flagged(signals: list[Signal], mode: str) -> bool:
    from loopcanary import Severity

    if not signals:
        return False
    if mode == "strict":
        return any(s.severity is Severity.ALERT for s in signals)
    return any(s.severity >= Severity.WARN for s in signals)


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    def f1(self) -> float:
        p, r = self.precision(), self.recall()
        return 2 * p * r / (p + r) if (p + r) else 0.0


def evaluate(path: Path, mode: str, positive_labels: frozenset[str]) -> dict[str, Counts]:
    """Run detectors over every trajectory; return per-detector + pooled counts.

    A fresh `Canary` (fresh detector state) is used per trajectory — the same
    isolation an RL rollout worker would use.
    """
    detector_names = [d.name for d in default_detectors()]
    per_detector = {name: Counts() for name in detector_names}
    pooled = Counts()

    n = 0
    for traj in iter_trajectories(path, positive_labels):
        n += 1
        canary = Canary()
        signals: list[Signal] = []
        for event in traj.events:
            signals.extend(canary.observe(event))

        # pooled: did ANY detector flag this trajectory?
        pooled_flag = _flagged(signals, mode)
        _tally(pooled, traj.is_positive, pooled_flag)

        # per-detector: did THIS detector flag it?
        for name in detector_names:
            det_signals = [s for s in signals if s.detector == name]
            _tally(per_detector[name], traj.is_positive, _flagged(det_signals, mode))

    if n == 0:
        raise SystemExit(
            "error: dataset yielded zero trajectories — check the path and schema "
            f"(see TRACE_FIELDS in {Path(__file__).name})."
        )
    return {"__pooled__": pooled, **per_detector}


def _tally(counts: Counts, is_positive: bool, flagged: bool) -> None:
    if is_positive and flagged:
        counts.tp += 1
    elif is_positive and not flagged:
        counts.fn += 1
    elif not is_positive and flagged:
        counts.fp += 1
    else:
        counts.tn += 1


def _print_report(results: dict[str, Counts], mode: str, dataset: Path) -> None:
    print(f"\nloopcanary validation — dataset={dataset.name} detection={mode}\n")
    header = f"{'detector':<22}{'P':>8}{'R':>8}{'F1':>8}{'TP':>6}{'FP':>6}{'FN':>6}{'TN':>6}"
    print(header)
    print("-" * len(header))
    # pooled first, then per-detector
    order = ["__pooled__"] + [k for k in results if k != "__pooled__"]
    for name in order:
        c = results[name]
        label = "POOLED (any detector)" if name == "__pooled__" else name
        print(
            f"{label:<22}{c.precision():>8.3f}{c.recall():>8.3f}{c.f1():>8.3f}"
            f"{c.tp:>6}{c.fp:>6}{c.fn:>6}{c.tn:>6}"
        )
    print(
        "\nPaste these into the README validation table only after running on the "
        "real dataset. Do not fabricate.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_trace.py",
        description="Score loopcanary detectors against a labeled trace dataset.",
    )
    parser.add_argument("--dataset", required=True, type=Path,
                        help="path to a JSONL trace dataset (see module docstring for schema)")
    parser.add_argument("--detection", choices=DETECTION_MODES, default="lenient",
                        help="detection definition (default: lenient)")
    parser.add_argument("--positive-labels", default=",".join(sorted(DEFAULT_POSITIVE_LABELS)),
                        help="comma-separated labels that count as positive (degenerate)")
    args = parser.parse_args(argv)

    if not args.dataset.exists():
        raise SystemExit(
            f"error: dataset not found: {args.dataset}\n"
            "This script does not ship a dataset. Point --dataset at a downloaded "
            "TRACE (or compatible) JSONL file. Until then, README metrics stay as "
            "'[to be filled by a validation run]'."
        )

    positive = frozenset(s.strip().lower() for s in args.positive_labels.split(",") if s.strip())
    results = evaluate(args.dataset, args.detection, positive)
    _print_report(results, args.detection, args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
