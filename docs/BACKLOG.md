# Backlog

Everything deliberately left out of v1.0. Each entry is a decision, not a
TODO — items land here so the v1 scope stays frozen. Tagged for triage.

## adapter-wanted

- **Codex adapter** — consume OpenAI Codex CLI session output → `LoopEvent`
  stream. Same shape as the Claude Code transcript adapter.
- **LangGraph adapter** — hook LangGraph's node/edge callbacks into a
  `Canary`.
- **AutoGen adapter** — instrument AutoGen agent turns.
- **OpenTelemetry ingestion** — read OTel `gen_ai.*` spans and map to
  `LoopEvent`s, so an existing traced pipeline can feed loopcanary
  without code changes. Also: emit our signals as OTel events so Tier-1
  platforms become distribution, not competition.

## detectors-wanted

- **Entropy / logprob / distributional detectors** — `LoopEvent.model_signals`
  already carries `mean_logprob` / `entropy` for exactly this. v1
  detectors do not read it. A distributional detector (e.g., collapse in
  output entropy = degeneration) is the first v1.1 detector for
  local/open models where logprobs are available.
- **LLM-judge second-stage detector** — the cascade interface supports a
  detector that `consumes` signals and confirms them with a model call.
  We ship the interface, not the judge (that's a research/opt-in extra,
  and it's the one thing that would send data out of the process).
- **Learned probe detector** — a small classifier over event features as
  a second-stage confirm. Same cascade slot as the judge.

## capabilities-deferred

- **Codex / Claude Code hook-mode adapters** — run as an external hook
  the CLI invokes per tool event (vs. tailing the transcript). More
  real-time than transcript mode. Deferred: transcript mode covers the
  demo; hook mode is per-tool plumbing.
- **Distributional field consumption** — see detectors-wanted; the field
  exists in the schema now, unread.

## explicitly-not-doing (v1 non-goals — here so nobody re-proposes them)

- Dashboard / UI / web / server / backend — re-enters the platform tier.
- Any network I/O in core. Zero egress is load-bearing.
- Auto-intervention / loop-breaking / retry — signals only; the caller
  decides what to do.
- Aggregate "trajectory health score" — we emit named, legible signals,
  not a composite number.
- Persistence / databases / config frameworks / plugin entry-point systems.
- Effectiveness/monitorability *claims* in docs — that's future research,
  not a README sentence.
