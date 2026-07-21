---
# StyleScout — Development Rules

Read this file before every task. It overrides any assumption you might make.

## Product contract
- Three real modes: `my_wardrobe` | `wardrobe_plus_ai` | `ai_inspiration`
- Every outfit item MUST carry: `source` ("wardrobe" | "suggested") and `owned` (bool)
- Mode 1 MUST NOT return any item outside the wardrobe. Enforced in code, never left to the prompt.
- Mode 2: maximum 2 suggested (unowned) items per outfit
- Mode 3: generate the ideal outfit with NO wardrobe in context, then run the ownership resolver

## Architecture
- Do NOT create new agents. There are exactly two: `StylistAgent`, `InlineEditAgent`
- An "agent" calls an LLM. Everything else is a deterministic SERVICE.
- Memory / Wardrobe / Shopping are services, not agents.
- The LLM proposes, deterministic code decides.
- Every LLM output is validated with Pydantic: schema → referential → constraint → coherence.
  On failure: exactly 1 repair attempt, then fall back to the deterministic composer.
- The existing rule-based composer is NOT dead code. It is the deterministic fallback path.
  Never delete it. Never bypass it.
- Ranking is deterministic. All weights live in a single config object.
- `AgentContext` carries: user_id, mode, preferences, wardrobe snapshot, request text, trace_id.

## Hard nos
- NO scraping, ever
- NO fake product or price data. Shopping = deep links to real marketplace searches only.
- NO React migration. Frontend stays vanilla JS, organised into modules.
- NO auth in MVP (but `user_id` must exist on every record from day one)
- NO AI scores shown to the user (e.g. "8.2 color harmony")
- NO new dependencies without a record in docs/DECISIONS.md

## Definition of done
Every change: tests pass + a record is appended to docs/DECISIONS.md.

## Prompt format expected from the developer
Context → Goal → Files to change → Constraint → Acceptance criteria → Do not do
---
