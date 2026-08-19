# StyleScout evaluation report (SCOUT-015)

Generated: 2026-08-19T12:35:28Z

> **Latency note:** All latency figures are **local, in-process** measurements via FastAPI `TestClient`. They are **not** production or live-deployment SLA claims.

## Summary metrics

| Metric | Value |
|--------|------:|
| Mode 1 compliance | 100.0% |
| Schema validity | 51.52% |
| Provenance correctness | 45.45% |
| Mode 2 cap adherence (≤2 suggested) | 30.77% |
| Search spec honors preferences | 0.0% |
| p50 latency (ms, in-process) | 8.87 |

Fixtures run: 33

### Validation paths observed

- `fallback`: 1 fixture(s)
- `repair`: 1 fixture(s)
- `validated`: 15 fixture(s)

## Other fixture failures

- **`wpa_empty_casual`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_empty_formal`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_empty_weekend`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_partial_casual`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_partial_office`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_partial_evening`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_empty_casual`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_empty_elegant`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_empty_minimal`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_partial_casual`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_partial_office`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_partial_weekend`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_full_casual`**: ai_inspiration outfit item 'Blue Jeans' matches wardrobe but is not marked owned; ai_inspiration outfit item 'White Sneakers' matches wardrobe but is not marked owned
- **`ai_full_edgy`**: ai_inspiration outfit item 'Blue Jeans' matches wardrobe but is not marked owned; ai_inspiration outfit item 'White Sneakers' matches wardrobe but is not marked owned
- **`wpa_partial_prefs`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_empty_prefs`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`ai_partial_prefs`**: request raised ValueError: Wardrobe item is missing a persisted id.
- **`wpa_partial_repair_cap`**: request raised ValueError: Wardrobe item is missing a persisted id.

## Per-fixture results

| ID | Mode | Wardrobe | ms | Schema | Provenance | Mode1 | Cap | Path |
|----|------|----------|---:|--------|------------|-------|-----|------|
| mw_empty_casual | my_wardrobe | empty | 17.9 | pass | pass | pass | — | validated |
| mw_empty_dinner | my_wardrobe | empty | 7.1 | pass | pass | pass | — | validated |
| mw_empty_office | my_wardrobe | empty | 4.9 | pass | pass | pass | — | validated |
| mw_partial_casual | my_wardrobe | partial | 5.7 | pass | pass | pass | — | validated |
| mw_partial_dinner | my_wardrobe | partial | 6.4 | pass | pass | pass | — | validated |
| mw_partial_rain | my_wardrobe | partial | 8.1 | pass | pass | pass | — | validated |
| mw_full_casual | my_wardrobe | full | 11.1 | pass | pass | pass | — | validated |
| mw_full_dinner | my_wardrobe | full | 6.7 | pass | pass | pass | — | validated |
| mw_full_coat | my_wardrobe | full | 6.5 | pass | pass | pass | — | validated |
| wpa_empty_casual | wardrobe_plus_ai | empty | 12.0 | FAIL | FAIL | — | FAIL | — |
| wpa_empty_formal | wardrobe_plus_ai | empty | 7.7 | FAIL | FAIL | — | FAIL | — |
| wpa_empty_weekend | wardrobe_plus_ai | empty | 6.5 | FAIL | FAIL | — | FAIL | — |
| wpa_partial_casual | wardrobe_plus_ai | partial | 6.8 | FAIL | FAIL | — | FAIL | — |
| wpa_partial_office | wardrobe_plus_ai | partial | 6.5 | FAIL | FAIL | — | FAIL | — |
| wpa_partial_evening | wardrobe_plus_ai | partial | 8.3 | FAIL | FAIL | — | FAIL | — |
| wpa_full_casual | wardrobe_plus_ai | full | 10.8 | pass | pass | — | pass | validated |
| wpa_full_gaps | wardrobe_plus_ai | full | 8.9 | pass | pass | — | pass | validated |
| wpa_full_travel | wardrobe_plus_ai | full | 18.1 | pass | pass | — | pass | validated |
| ai_empty_casual | ai_inspiration | empty | 11.8 | FAIL | FAIL | — | — | — |
| ai_empty_elegant | ai_inspiration | empty | 8.9 | FAIL | FAIL | — | — | — |
| ai_empty_minimal | ai_inspiration | empty | 17.4 | FAIL | FAIL | — | — | — |
| ai_partial_casual | ai_inspiration | partial | 12.2 | FAIL | FAIL | — | — | — |
| ai_partial_office | ai_inspiration | partial | 11.6 | FAIL | FAIL | — | — | — |
| ai_partial_weekend | ai_inspiration | partial | 12.8 | FAIL | FAIL | — | — | — |
| ai_full_casual | ai_inspiration | full | 21.7 | pass | FAIL | — | — | validated |
| ai_full_formal | ai_inspiration | full | 14.9 | pass | pass | — | — | validated |
| ai_full_edgy | ai_inspiration | full | 12.9 | pass | FAIL | — | — | validated |
| wpa_partial_prefs | wardrobe_plus_ai | partial | 12.2 | FAIL | FAIL | — | FAIL | — |
| wpa_empty_prefs | wardrobe_plus_ai | empty | 7.8 | FAIL | FAIL | — | FAIL | — |
| ai_partial_prefs | ai_inspiration | partial | 9.7 | FAIL | FAIL | — | — | — |
| mw_partial_repair | my_wardrobe | partial | 7.7 | pass | pass | pass | — | repair |
| wpa_partial_repair_cap | wardrobe_plus_ai | partial | 10.7 | FAIL | FAIL | — | FAIL | — |
| wpa_partial_fallback | wardrobe_plus_ai | partial | 10.3 | pass | pass | — | pass | fallback |
