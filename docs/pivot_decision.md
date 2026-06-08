# monitorstress pivot decision — recommendation

Companion to `docs/reading_notes.md` and `docs/malt_recon.md`. Written
2026-05-25, before the next plan revision.

## Recommendation (confidence: medium)

Pivot **toward a reformulated (D): a standardised, multi-monitor evaluation
suite for post-hoc agent integrity, where calibration is one dimension of
four or five rather than the headline contribution.** Do not commit to
pure (A-prime). The contribution is *comparison across monitors and
operating conditions on a stable substrate*, not building a better monitor
or being first to publish calibration numbers. Confidence is medium, not
high, because the empirical pilot was not executed in this session (HF
auth blocker), and a critical reproduction question — does a Claude
monitor on the verbatim METR prompt land near METR's reported numbers? —
remains unanswered. Reformulation, not abandonment, of the previous
working hypothesis: "measurement infrastructure for scalable oversight"
stays as motivation; "calibrated post-hoc monitors" narrows from "v1
contribution" to "one of several axes in the evaluation suite."

## Key evidence

The (A-prime)-pure-play case is undermined by three specific findings.
**Griffin et al. (UK AISI, 15 Aug 2025) already run ordinary-distribution
calibration on a 2,997-example MALT+ControlArena+WildChat mix at 0.1%
positive rate** (`docs/reading_notes.md` §1) — that is the (A-prime) story.
They report 7% recall on METR reward hacking and acknowledge only "3
positive-labels for our 0.1% OPR." A monitorstress (A-prime) paper has to
differentiate concretely against this; "we did calibration on MALT" is
not enough. **Radharapu et al.'s linear-probe method requires
residual-stream activations** (`docs/reading_notes.md` §2), so it cannot
calibrate a closed-API Claude/GPT judge as-published; the obvious tool
for tighter calibration is partially blocked unless monitorstress accepts a
local-judge-only constraint. **METR's own monitors are at 0.96
reward-hacking AUROC for GPT-5** (`docs/reading_notes.md` §3); point
AUROC is at ceiling, so any monitorstress contribution that *only* moves
that number is publishable but small. The room is in calibration *plus*
obfuscation robustness *plus* coverage *plus* multi-monitor comparison —
which is exactly the (D) framing. The debate-literature framing
(`docs/reading_notes.md` §4) is rhetorically nice but Kenton et al. (2024)
weaken it enough that it should be motivation only, not load-bearing for
the contribution claim.

## Key risks the recommendation does not yet address

Three. (1) **The empirical pilot was not run** — the headline number "does
Claude on METR's verbatim prompt approximately reproduce METR's results"
is unknown, and a wide gap there would change the project's options. (2)
**(D) requires multi-monitor comparison**, which in turn requires
API spend at a higher volume than the $10 session cap — credible
cross-monitor evaluation (say, three monitors × MALT × four obfuscation
variants) is a real budget item in the low hundreds of dollars, and the
project plan should size that explicitly. (3) **MALT's per-category sample
sizes are tight enough** (`docs/malt_recon.md`) that calibration claims
restricted to MALT alone will have wide CIs at the long-tail labels; (D)
likely needs a second corpus (RHA, EvilGenie, or a monitorstress-collected
supplement) for the calibration dimension to be more than a point estimate.

## Concrete next two weeks if accepted

- **Day 1:** Fix HF auth. Run `notebooks/malt_recon.ipynb` end-to-end with
  a $5 spend cap. Land the 60-sample AUROC, ECE, and reliability diagram.
  Decision gate: if AUROC <0.85 on Claude-Sonnet-4-7 with METR's verbatim
  prompt, debug prompt/parsing before doing anything else.
- **Week 1:** Draft a 2-page "evaluation suite v0" spec — what dimensions
  (point AUROC, ECE, obfuscation robustness across the four METR variants
  plus a fifth adversarial variant, coverage on long-tail labels), which
  monitors (Claude, GPT, open-weight Qwen), which corpora (MALT + at
  least one supplementary). Circulate before any implementation.
- **Week 1:** Email/Slack Charlie Griffin and the AISI Control team. Their
  unpublished prompts/model-organisms would massively de-risk
  reproducibility, and the conversation is cheaper than re-deriving.
- **Week 2:** Reach out to the EvilGenie and RHA authors (you've already
  cited both in `README.md`'s Related Work). Ask: would your labelled
  hacks be usable as evaluation fixtures for a monitor-comparison suite?
- **Week 2:** Rewrite `monitorstress_plan.md` against the chosen direction.
  The v1 monitorstress ships as a small CLI that runs N monitors against M
  corpora and emits a calibration+robustness+coverage report card. Phase
  1 of the existing roadmap collapses into "implement the suite for one
  monitor × MALT × one obfuscation variant"; the rest is straightforward
  scaling.
