"""loopcanary — agent-loop observability SDK (in development).

loopcanary watches an agent's execution loop and diagnoses when its
behaviour is degrading, its context is compressing, or its cost is
running away — via named detectors and a per-run timeline.

This repository currently contains the **data-model seed** the SDK is
built on:

* :mod:`loopcanary.core.events` — the discriminated ``TrajectoryEvent``
  variants (reasoning, tool call, observation, scoring).
* :mod:`loopcanary.core.trajectory` — the ``Trajectory`` container.
* :mod:`loopcanary.core.verdict` — ``SemanticVerdict`` and the
  taxonomy, the shape every detector returns.

The v1.0 SDK surface (``watch()`` context manager, the ``Detector``
protocol, the initial detector set, the timeline report) is specified
in ``docs/pivot_v1_agentic.md`` and not yet implemented.

The pre-pivot batch experiments (MALT ingestion, structural
transformations, the METR reward-hacking monitor, AUROC report card)
and the SaTML research finding live in a separate repository,
`monitorstress <https://github.com/tianyi-zhang-02/monitorstress>`_.
The two repositories are intentionally independent and neither imports
the other.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
