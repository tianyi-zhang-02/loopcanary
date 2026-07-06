"""End-to-end test of the validation harness on synthetic data.

We can't ship the real TRACE dataset, but we can prove the whole pipeline —
JSONL loading, TRACE->LoopEvent mapping, detector run, metric computation —
works on a synthetic corpus with known ground truth. This is the test that
would catch a regression in `scripts/validate_trace.py` end to end.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/ is not a package; import the harness by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import validate_trace as vt  # noqa: E402


def _traj(id: str, label: str, steps: list[dict]) -> str:
    return json.dumps({"id": id, "label": label, "steps": steps})


def _stuck_steps(n: int) -> list[dict]:
    # identical action + identical output, n times -> a stuck loop.
    return [{"action": "python train.py --resume", "output": "FileNotFoundError"} for _ in range(n)]


def _healthy_steps(n: int) -> list[dict]:
    return [{"action": f"step-{i}", "output": f"result-{i}"} for i in range(n)]


def _write(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "synthetic.jsonl"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p


POSITIVE = frozenset({"degenerate"})


def test_strict_detection_separates_stuck_from_healthy(tmp_path: Path) -> None:
    rows = [
        _traj("d1", "degenerate", _stuck_steps(10)),   # ALERT-level stuck
        _traj("d2", "degenerate", _stuck_steps(12)),
        _traj("h1", "healthy", _healthy_steps(10)),
        _traj("h2", "healthy", _healthy_steps(10)),
    ]
    dataset = _write(tmp_path, rows)
    results = vt.evaluate(dataset, "strict", POSITIVE)

    pooled = results["__pooled__"]
    # both degenerate flagged, neither healthy flagged -> perfect on this toy set.
    assert pooled.tp == 2
    assert pooled.fn == 0
    assert pooled.fp == 0
    assert pooled.tn == 2
    assert pooled.precision() == 1.0
    assert pooled.recall() == 1.0
    assert pooled.f1() == 1.0


def test_lenient_flags_warn_only_trajectories(tmp_path: Path) -> None:
    # 3 identical steps -> repeated_action WARN, but never ALERT.
    rows = [
        _traj("d1", "degenerate", _stuck_steps(3)),
        _traj("h1", "healthy", _healthy_steps(10)),
    ]
    dataset = _write(tmp_path, rows)

    strict = vt.evaluate(dataset, "strict", POSITIVE)["__pooled__"]
    lenient = vt.evaluate(dataset, "lenient", POSITIVE)["__pooled__"]

    # strict (ALERT-only) misses the WARN-level stuck; lenient catches it.
    assert strict.tp == 0 and strict.fn == 1
    assert lenient.tp == 1 and lenient.fn == 0


def test_per_detector_breakdown_present(tmp_path: Path) -> None:
    rows = [_traj("d1", "degenerate", _stuck_steps(10))]
    dataset = _write(tmp_path, rows)
    results = vt.evaluate(dataset, "lenient", POSITIVE)
    # pooled plus each of the three deterministic detectors.
    assert "__pooled__" in results
    assert "repeated_action" in results
    assert "null_progress" in results
    assert "context_pressure" in results
    # repeated_action should own the true positive here.
    assert results["repeated_action"].tp == 1


def test_malformed_lines_skipped_not_fatal(tmp_path: Path) -> None:
    p = tmp_path / "mixed.jsonl"
    p.write_text(
        _traj("d1", "degenerate", _stuck_steps(10)) + "\n"
        "this is not json\n"
        + _traj("h1", "healthy", _healthy_steps(10)) + "\n",
        encoding="utf-8",
    )
    results = vt.evaluate(p, "strict", POSITIVE)
    pooled = results["__pooled__"]
    assert pooled.tp + pooled.fn == 1  # one degenerate
    assert pooled.tn + pooled.fp == 1  # one healthy


def test_empty_dataset_raises(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    try:
        vt.evaluate(p, "strict", POSITIVE)
    except SystemExit:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit on empty dataset")
