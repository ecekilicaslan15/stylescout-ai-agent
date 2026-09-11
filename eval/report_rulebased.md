# StyleScout evaluation report (SCOUT-015)

Generated: 2026-09-11T12:38:28Z

> **Latency note:** All latency figures are **local, in-process** measurements via FastAPI `TestClient`. They are **not** production or live-deployment SLA claims.

## Summary metrics

| Metric | Value |
|--------|------:|
| Mode 1 compliance | 100.0% |
| Schema validity | 100.0% |
| Provenance correctness | 100.0% |
| Mode 2 cap adherence (≤2 suggested) | 100.0% |
| Search spec honors preferences | 100.0% |
| p50 latency (ms, in-process) | 5.33 |

Fixtures run: 33
USE_LLM: False

### Validation paths observed

- `fallback`: 1 fixture(s)
- `repair`: 2 fixture(s)
- `validated`: 30 fixture(s)

## Per-fixture results

| ID | Mode | Wardrobe | ms | Schema | Provenance | Mode1 | Cap | Path |
|----|------|----------|---:|--------|------------|-------|-----|------|
| mw_empty_casual | my_wardrobe | empty | 14.1 | pass | pass | pass | — | validated |
| mw_empty_dinner | my_wardrobe | empty | 5.3 | pass | pass | pass | — | validated |
| mw_empty_office | my_wardrobe | empty | 3.5 | pass | pass | pass | — | validated |
| mw_partial_casual | my_wardrobe | partial | 3.7 | pass | pass | pass | — | validated |
| mw_partial_dinner | my_wardrobe | partial | 4.5 | pass | pass | pass | — | validated |
| mw_partial_rain | my_wardrobe | partial | 9.2 | pass | pass | pass | — | validated |
| mw_full_casual | my_wardrobe | full | 5.9 | pass | pass | pass | — | validated |
| mw_full_dinner | my_wardrobe | full | 4.8 | pass | pass | pass | — | validated |
| mw_full_coat | my_wardrobe | full | 5.4 | pass | pass | pass | — | validated |
| wpa_empty_casual | wardrobe_plus_ai | empty | 4.0 | pass | pass | — | pass | validated |
| wpa_empty_formal | wardrobe_plus_ai | empty | 5.0 | pass | pass | — | pass | validated |
| wpa_empty_weekend | wardrobe_plus_ai | empty | 4.6 | pass | pass | — | pass | validated |
| wpa_partial_casual | wardrobe_plus_ai | partial | 4.0 | pass | pass | — | pass | validated |
| wpa_partial_office | wardrobe_plus_ai | partial | 5.1 | pass | pass | — | pass | validated |
| wpa_partial_evening | wardrobe_plus_ai | partial | 7.9 | pass | pass | — | pass | validated |
| wpa_full_casual | wardrobe_plus_ai | full | 5.8 | pass | pass | — | pass | validated |
| wpa_full_gaps | wardrobe_plus_ai | full | 6.4 | pass | pass | — | pass | validated |
| wpa_full_travel | wardrobe_plus_ai | full | 6.8 | pass | pass | — | pass | validated |
| ai_empty_casual | ai_inspiration | empty | 4.2 | pass | pass | — | — | validated |
| ai_empty_elegant | ai_inspiration | empty | 4.1 | pass | pass | — | — | validated |
| ai_empty_minimal | ai_inspiration | empty | 5.3 | pass | pass | — | — | validated |
| ai_partial_casual | ai_inspiration | partial | 4.1 | pass | pass | — | — | validated |
| ai_partial_office | ai_inspiration | partial | 3.9 | pass | pass | — | — | validated |
| ai_partial_weekend | ai_inspiration | partial | 5.0 | pass | pass | — | — | validated |
| ai_full_casual | ai_inspiration | full | 5.3 | pass | pass | — | — | validated |
| ai_full_formal | ai_inspiration | full | 6.1 | pass | pass | — | — | validated |
| ai_full_edgy | ai_inspiration | full | 7.0 | pass | pass | — | — | validated |
| wpa_partial_prefs | wardrobe_plus_ai | partial | 5.6 | pass | pass | — | pass | validated |
| wpa_empty_prefs | wardrobe_plus_ai | empty | 6.2 | pass | pass | — | pass | validated |
| ai_partial_prefs | ai_inspiration | partial | 5.7 | pass | pass | — | — | validated |
| mw_partial_repair | my_wardrobe | partial | 7.1 | pass | pass | pass | — | repair |
| wpa_partial_repair_cap | wardrobe_plus_ai | partial | 6.5 | pass | pass | — | pass | repair |
| wpa_partial_fallback | wardrobe_plus_ai | partial | 6.7 | pass | pass | — | pass | fallback |
