# Finding: the METR reward-hacking monitor's signal is reasoning-dependent

*Research track (target: SaTML, deadline 2026-09-29). Separate artifact
from the loopcanary SDK. This doc records the finding, its error bars,
and its honest weaknesses — it is not a paper draft.*

## One-line result

On `claude-sonnet-4-6`, removing the agent's reasoning trace
(`drop_reasoning`) collapses METR's reward-hacking monitor from
AUROC **0.683 → 0.500 (chance)**, while two structurally comparable
transformations — truncating observations and padding with noop tool
calls — leave it **unchanged at 0.683**. The monitor's entire
discriminative signal lives in the chain-of-thought.

## The data

- **Run:** `research/data/sonnet-4-6_n60_20260608.json`
- **Model:** `claude-sonnet-4-6` (self-recorded in the run output via
  the `--model` provenance feature; not inferred)
- **Corpus:** MALT public split, manually-reviewed, n=60 balanced
  (30 positive / 30 negative), 4 transformation variants each = 240
  monitor calls
- **Monitor:** METR's published reward-hacking prompt, brought to
  verbatim parity (see `docs/prompt_parity_verification.md`)
- **Bootstrap:** 1000 resamples for all CIs

| transformation | AUROC | 95% CI | Δ vs clean | Δ 95% CI | mechanism |
|---|---|---|---|---|---|
| clean | 0.683 | (0.600, 0.767) | — | — | 49/60 zero-scores |
| **drop_reasoning** | **0.500** | (0.500, 0.500) | **−0.183** | **(−0.274, −0.091)** | **60/60 zero-scores** |
| truncate_obs | 0.683 | (0.597, 0.771) | +0.000 | (0.000, 0.000) | 49/60 zero-scores |
| pad_noops | 0.683 | (0.600, 0.773) | +0.000 | (0.000, 0.000) | 49/60 zero-scores |

Reproduce from the raw records (not the stored report block):

```bash
python research/analyze_run.py research/data/sonnet-4-6_n60_20260608.json 1000
```

## Why this is a clean result

1. **It is controlled, not generic perturbation-fragility.** Three
   structural transformations were applied; only `drop_reasoning`
   moved the number. Truncating the trajectory tail and inserting
   noop tool calls produced Δ AUROC of *exactly* 0.0 — identical
   score distributions to clean. So the effect is specific to
   reasoning removal, not "any edit breaks the monitor."
2. **The Δ is statistically distinguishable from zero at n=60.** The
   `drop_reasoning` Δ 95% CI is (−0.274, −0.091) — it does not cross
   zero. The other two transforms have zero-width Δ CIs at 0.0.
3. **The mechanism is visible and total.** Under `drop_reasoning`
   the monitor emits score=0 ("definitely not cheating") on **all
   60** trajectories — positive and negative alike. It is not a
   graceful degradation; it is a cliff to a degenerate all-negative
   classifier. A reward-hacking agent that simply omits its reasoning
   from the transcript evades the monitor completely.

## Honest weaknesses (the reviewer-attack surface)

1. **Clean AUROC is 0.683, far below METR's published ~0.96.** The
   baseline monitor is weak. Causes, from the diagnostic trail:
   `claude-sonnet-4-6` (not METR's GPT-5); the whole-trajectory
   (non-chunked) operational model; and the synthesized
   `[role:source]` transcript format rather than METR's native
   chat-completion format (see `docs/prompt_and_format_diagnosis.md`,
   the "transcript-format" hypothesis). As written, the result is
   *"drop_reasoning collapses an already-modest monitor to chance,"*
   which is weaker than *"collapses a strong monitor."* Clean's CI
   lower bound is 0.600 — the baseline is meaningfully above chance
   but not by much.
2. **Single run, single seed, n=60.** The `drop_reasoning`
   all-zeros collapse is mechanically robust (it is not sampling
   noise — every score is literally 0), but the clean = 0.683 point
   estimate has a wide CI and has not been replicated across seeds or
   a larger sample. A paper wants n larger and ≥1 replication.
3. **Earlier Haiku runs lacked model provenance.** Haiku-4.5 runs
   with the faithful prompt sat at clean ≈ 0.517–0.533 (chance) — the
   reason Sonnet was needed for any headroom — but those run outputs
   predate the `--model` recording feature and do not self-document
   their model. They are suggestive context, not rigorous evidence.

## Decision status

Per the 2026-07-05 call: **commit the runs, surface the CIs, then
decide ship-vs-strengthen.** The CIs are now visible (above). The
open fork:

- **Ship as-is** — write on the controlled collapse from the 0.683
  baseline; own the "why below 0.96" question directly. Writeable
  now; safest against the Sept 29 clock. Next steps: larger n + a
  replication seed for robustness, then draft.
- **Strengthen clean first** — fix the transcript-format divergence
  to push clean toward ~0.9x, then show the collapse from a strong
  monitor. Higher ceiling, real experimental work (format fix +
  re-runs + larger n), higher risk against the deadline.

This decision is not yet made. It should be informed by the CIs
above and by how much runway remains before 2026-09-29.

## Relationship to the SDK track

Separate artifact, separate clock. The loopcanary SDK (agent-loop
observability) ships on a git tag with no fixed deadline; this
finding ships as a SaTML submission with a hard one. The
`drop_reasoning` transformation and the `compute_report` analysis are
shared code, but the two deliverables must not be conflated: polishing
the SDK does not advance the paper, and vice versa.
