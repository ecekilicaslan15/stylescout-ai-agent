# StyleScout evaluation report (SCOUT-015)

Generated: 2026-09-11T12:40:47Z

> **Latency note:** All latency figures are **local, in-process** measurements via FastAPI `TestClient`. They are **not** production or live-deployment SLA claims.

## Summary metrics

| Metric | Value |
|--------|------:|
| Mode 1 compliance | 100.0% |
| Schema validity | 100.0% |
| Provenance correctness | 100.0% |
| Mode 2 cap adherence (≤2 suggested) | 100.0% |
| Search spec honors preferences | 100.0% |
| p50 latency (ms, in-process) | 248.58 |

Fixtures run: 33
USE_LLM: True

### Validation paths observed

- `fallback`: 1 fixture(s)
- `repair`: 2 fixture(s)
- `validated`: 30 fixture(s)

### LLM planner observability (this run)

- Plan-level JSON failures (`llm_plan_error_count`): 33
- Rate-limit fallbacks after retry (`llm_rate_limited_count`): 0
- Inter-request delay: 3.5s (harness-only)

## Per-fixture results

| ID | Mode | Wardrobe | ms | Schema | Provenance | Mode1 | Cap | Path |
|----|------|----------|---:|--------|------------|-------|-----|------|
| mw_empty_casual | my_wardrobe | empty | 531.0 | pass | pass | pass | — | validated |
| mw_empty_dinner | my_wardrobe | empty | 283.4 | pass | pass | pass | — | validated |
| mw_empty_office | my_wardrobe | empty | 241.1 | pass | pass | pass | — | validated |
| mw_partial_casual | my_wardrobe | partial | 259.7 | pass | pass | pass | — | validated |
| mw_partial_dinner | my_wardrobe | partial | 221.2 | pass | pass | pass | — | validated |
| mw_partial_rain | my_wardrobe | partial | 244.9 | pass | pass | pass | — | validated |
| mw_full_casual | my_wardrobe | full | 199.3 | pass | pass | pass | — | validated |
| mw_full_dinner | my_wardrobe | full | 252.0 | pass | pass | pass | — | validated |
| mw_full_coat | my_wardrobe | full | 298.6 | pass | pass | pass | — | validated |
| wpa_empty_casual | wardrobe_plus_ai | empty | 222.8 | pass | pass | — | pass | validated |
| wpa_empty_formal | wardrobe_plus_ai | empty | 265.6 | pass | pass | — | pass | validated |
| wpa_empty_weekend | wardrobe_plus_ai | empty | 263.8 | pass | pass | — | pass | validated |
| wpa_partial_casual | wardrobe_plus_ai | partial | 222.0 | pass | pass | — | pass | validated |
| wpa_partial_office | wardrobe_plus_ai | partial | 252.3 | pass | pass | — | pass | validated |
| wpa_partial_evening | wardrobe_plus_ai | partial | 247.2 | pass | pass | — | pass | validated |
| wpa_full_casual | wardrobe_plus_ai | full | 205.4 | pass | pass | — | pass | validated |
| wpa_full_gaps | wardrobe_plus_ai | full | 219.9 | pass | pass | — | pass | validated |
| wpa_full_travel | wardrobe_plus_ai | full | 232.7 | pass | pass | — | pass | validated |
| ai_empty_casual | ai_inspiration | empty | 276.9 | pass | pass | — | — | validated |
| ai_empty_elegant | ai_inspiration | empty | 270.8 | pass | pass | — | — | validated |
| ai_empty_minimal | ai_inspiration | empty | 275.6 | pass | pass | — | — | validated |
| ai_partial_casual | ai_inspiration | partial | 269.6 | pass | pass | — | — | validated |
| ai_partial_office | ai_inspiration | partial | 243.1 | pass | pass | — | — | validated |
| ai_partial_weekend | ai_inspiration | partial | 245.8 | pass | pass | — | — | validated |
| ai_full_casual | ai_inspiration | full | 243.0 | pass | pass | — | — | validated |
| ai_full_formal | ai_inspiration | full | 217.6 | pass | pass | — | — | validated |
| ai_full_edgy | ai_inspiration | full | 238.7 | pass | pass | — | — | validated |
| wpa_partial_prefs | wardrobe_plus_ai | partial | 261.4 | pass | pass | — | pass | validated |
| wpa_empty_prefs | wardrobe_plus_ai | empty | 246.4 | pass | pass | — | pass | validated |
| ai_partial_prefs | ai_inspiration | partial | 248.6 | pass | pass | — | — | validated |
| mw_partial_repair | my_wardrobe | partial | 264.1 | pass | pass | pass | — | repair |
| wpa_partial_repair_cap | wardrobe_plus_ai | partial | 506.5 | pass | pass | — | pass | repair |
| wpa_partial_fallback | wardrobe_plus_ai | partial | 346.7 | pass | pass | — | pass | fallback |
