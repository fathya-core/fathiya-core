# FATHIYA OpenRouter Fusion Routing Card v1

Source: OpenRouter email PDF, "Deep research performance gains with multi-model Fusion", received 2026-06-17.

## Operational Lesson

OpenRouter's mid-June 2026 update is useful for FATHIYA as a routing strategy, not as a blanket model swap. The main pattern is lower cost per correct answer:

- Start routine planning and synthesis on cheap or free models.
- Escalate to an advisor model only when the cheap route is uncertain or stuck.
- Use subagents for bounded routine subtasks so the stronger model is not doing mechanical work.
- Use `openrouter/fusion` only for research-heavy tasks where multiple models and web-grounded synthesis are worth the extra reasoning.
- Keep `openrouter/fusion` out of default coding-agent, general chat, and one-second trading loops.

## Runtime Defaults

- Default planning fallback chain stays cheap/free through `OPENROUTER_MODEL_CANDIDATES`.
- Trading advisory stays on a short-lived `veto_only` path and cannot originate orders.
- Deep research model: `openrouter/fusion`.
- Safety guardrail model: `nvidia/nemotron-3.5-content-safety:free`.

## When To Trigger Fusion

Use Fusion for:

- Deep bug-bounty dedupe review across disclosed reports, source code, advisories, and vendor objections.
- Learning missions that need disagreement mapping across sources.
- Market or regulatory research where freshness and conflicting evidence matter.

Avoid Fusion for:

- The paper-trading one-second loop.
- Normal runtime planning.
- Simple status checks.
- Routine code edits or build/test cycles.

## Fusion Mechanics To Preserve

- `openrouter/fusion` can be called directly as a model slug for research-heavy questions.
- Fusion can also be invoked as a server tool from another model when the current question deserves deeper synthesis.
- The panel can include up to eight models plus a judge model that synthesizes the panel.
- Panel models and the judge use web search by default, so Fusion should be preferred when freshness matters.
- The judge should not be treated as a majority vote. It should map agreement, disagreement, unique catches, and blind spots before the final answer is written.

## Server Tools Pattern

- Advisor should be used for escalation, not as the default planner: call a stronger model only when the cheap/free route is stuck, uncertain, or conflicts with evidence.
- Advisor now supports multiple named advisors, memory across requests, and streaming; FATHIYA should represent this as optional escalation state, not permanent authority.
- Subagent is for self-contained routine subtasks during generation so the expensive model is not doing mechanical work.
- Fusion is for research-heavy synthesis where disagreement mapping and fresh web grounding change the quality of the answer.
- OpenRouter provider routing remains a separate optimization layer: default load balancing is acceptable, `:floor` is for cheapest paid-provider routing, `:nitro` is for speed-sensitive paid-provider routing, and Auto Router is a research candidate rather than FATHIYA's default planner.

## Cost Controls From The Email

- Optimize for cost per correct answer, not cost per token.
- Use cheap/free routes first, then escalate only when uncertainty, conflict, or missing evidence justifies it.
- Use Advisor for stuck or high-uncertainty steps instead of promoting the whole task to a frontier model.
- Use Subagent for bounded routine subtasks so expensive models do not perform mechanical work.
- When a paid OpenRouter route is explicitly allowed later, prefer `:floor` or `max_price` controls before raising model quality.
- Use `:nitro` only when latency matters more than cost and the operator has explicitly allowed paid routing.
- Use the Models API filters for price, modality, context, provider, and benchmark metadata before adding a model to FATHIYA's default chain.

## Model Notes From The Email

- `nex-agi/nex-n2-pro:free` remains useful as an agentic free advisor candidate.
- `nvidia/nemotron-3-ultra-550b-a55b` has a no-cost endpoint for evaluation and is already part of FATHIYA's free route.
- `nvidia/nemotron-3.5-content-safety:free` should be treated as a free guardrail candidate, not a general reasoning fallback.
- Paid/low-cost models such as Qwen3.7 Plus and Kimi K2.7 Code are optional future work, not default until the operator chooses paid routing.
- Qwen3.7 Plus is a 1M-context generalist candidate; only consider it for paid workhorse routing after explicit operator approval.
- Kimi K2.7 Code is a long-context coding-agent candidate; only consider it for paid agent coding after explicit operator approval.

## FATHIYA Implementation Rule

Expose the strategy through the local runtime without spending tokens during readiness probes. A task may request `openrouter_model_strategy` to show the exact configured model chain, Fusion route, advisor route, and safety model.
