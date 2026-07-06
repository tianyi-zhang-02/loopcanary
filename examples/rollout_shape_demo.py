"""rollout_shape_demo — the shape loopcanary takes inside an RL rollout worker.

The point of this demo is the *usage shape*, not any RL framework. An
on-policy RL loop (GRPO / PPO-style) samples many short rollouts per prompt,
often 16+ in parallel per worker. loopcanary is designed to ride inside one:

  * one `Canary` per rollout (fresh detector state, no cross-rollout leakage),
  * microsecond-per-event cost, no network, no model calls,
  * a compact `summary()` you fold into the rollout's reward/telemetry.

Here we simulate a batch of short rollouts — some healthy, some that collapse
into a repeated action — and aggregate the per-rollout summaries into a
batch-level view a training loop could log or use to down-weight degenerate
rollouts. There are **no NeMo-RL / TRL / framework imports**; this is the
integration *shape*, deliberately dependency-free.

Run:  python examples/rollout_shape_demo.py
"""

from __future__ import annotations

import random
from collections import Counter

from loopcanary import Canary, Severity


def healthy_rollout(rng: random.Random, length: int) -> list[tuple[str, str]]:
    """A rollout that makes progress: varied actions, varied outputs."""
    return [(f"act-{rng.randrange(10_000)}", f"obs-{rng.randrange(10_000)}") for _ in range(length)]


def collapsed_rollout(rng: random.Random, length: int) -> list[tuple[str, str]]:
    """A rollout that collapses: after a couple steps it repeats one action."""
    steps = [(f"act-{rng.randrange(10_000)}", f"obs-{rng.randrange(10_000)}") for _ in range(2)]
    steps += [("retry_same_tool_call", "same_error") for _ in range(length - 2)]
    return steps


def run_rollout(steps: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    """Instrument one rollout with its own Canary; return its summary."""
    canary = Canary()  # one per rollout — the isolation an RL worker needs
    for action, output in steps:
        canary.observe_raw(action=action, output=output, action_type="tool:step")
    return canary.summary()


def main() -> None:
    rng = random.Random(0)
    n_rollouts = 16  # a typical GRPO group size
    rollout_len = 12

    per_rollout: list[dict[str, dict[str, int]]] = []
    degenerate_flags: list[bool] = []

    for i in range(n_rollouts):
        # ~1 in 3 rollouts collapses, to make the batch view interesting.
        collapsed = (i % 3 == 0)
        steps = (collapsed_rollout if collapsed else healthy_rollout)(rng, rollout_len)
        summary = run_rollout(steps)
        per_rollout.append(summary)

        # a training loop's decision: did any detector reach ALERT?
        alerted = any(s.get("ALERT", 0) > 0 for s in summary.values())
        degenerate_flags.append(alerted)
        tag = "ALERT" if alerted else "ok"
        print(f"rollout {i:2d}: {'collapsed' if collapsed else 'healthy ':>9}  -> {tag}")

    # batch-level aggregation a worker could log or feed into reward shaping.
    batch_counts: Counter[str] = Counter()
    for summary in per_rollout:
        for detector, counts in summary.items():
            for sev in ("INFO", "WARN", "ALERT"):
                batch_counts[f"{detector}.{sev}"] += counts.get(sev, 0)

    flagged = sum(degenerate_flags)
    print(f"\nBatch: {flagged}/{n_rollouts} rollouts flagged degenerate (ALERT).")
    print("Aggregated signal counts across the batch:")
    for key in sorted(batch_counts):
        if batch_counts[key]:
            print(f"  {key}: {batch_counts[key]}")

    # a one-liner a reward function might use: fraction of clean rollouts.
    clean_fraction = 1.0 - flagged / n_rollouts
    print(f"\nclean_fraction = {clean_fraction:.3f}  "
          f"(the kind of scalar you might log per step or mix into a penalty)")

    # keep Severity imported-and-used so the example shows the enum is public.
    assert Severity.ALERT > Severity.WARN


if __name__ == "__main__":
    main()
