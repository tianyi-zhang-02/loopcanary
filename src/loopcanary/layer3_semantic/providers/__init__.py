"""LLM provider backends for the Layer 3 judge.

Every provider implements the abstract :class:`LLMProvider` interface
from :mod:`loopcanary.layer3_semantic.providers.base` — accept a list
of chat messages, return a
:class:`~loopcanary.core.verdict.SemanticVerdict` — so that the
escalation policy can swap them freely. Providers return the verdict
with ``escalated=False``; the
:class:`~loopcanary.layer3_semantic.judge.SemanticJudge` stamps
escalation provenance when it promotes between tiers.

Available backends:

* :mod:`loopcanary.layer3_semantic.providers.vllm_provider` — local
  vLLM-served open model (Qwen 2.5 7B by default).
* :mod:`loopcanary.layer3_semantic.providers.anthropic_provider` —
  Anthropic Claude API.
* :mod:`loopcanary.layer3_semantic.providers.openai_provider` —
  OpenAI API.
"""

from __future__ import annotations
