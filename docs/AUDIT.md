# StyleScout — MVP Audit

> Date: 2026-07-21  
> Method: File read (no guessing). Uncertain lines marked with `?`.  
> Reference: `AGENTS.md` target contract vs current code.

---

## Endpoints

Source: `api/main.py` (lines 245–295) + `StaticFiles` mount (line 295).

| Endpoint | Status | Note |
|----------|--------|------|
| `GET /api/health` | **real** | Returns `{"status":"ok"}`; no orchestrator/DB. |
| `GET /api/wardrobe/items` | **real** | `WardrobeService.list_items()` → JSON/SQLite repo; frontend shape via serializer. |
| `POST /api/outfits` | **partial** | `run_fashion_agent()` works end-to-end. Gaps: no `mode` parameter (no hybrid/inspiration); items lack `source`/`owned` (`AGENTS.md` target); `wardrobe_update` errors swallowed (267–268); memory/wardrobe NLP side effects silent. |
| `POST /api/outfits/inline-edit` | **partial** | `run_inline_edit()` is real. Gaps: frontend sends fixed instruction; agent errors may return HTTP 200 + `success:false`; no free-text UI. |
| `GET /` (and static assets) | **real** | `StaticFiles(FRONTEND_DIR, html=True)` — serves `frontend/index.html`. |
| `GET /api/memory` | **missing** | — |
| `POST /api/wardrobe/items` | **missing** | — |

---

## Agents & Services

### Classes under `agents/` — LLM call?

| Class | File | Calls LLM? | Note |
|-------|------|------------|------|
| `BaseAgent` | `agents/base_agent.py` | No | Abstract base class |
| `StylistAgent` | `agents/stylist_agent.py` | **No** | Rule-based `generate_outfit()` + keyword `RagService`. Agent retained per `AGENTS.md`. |
| `InlineEditAgent` | `agents/inline_edit_agent.py` | **No** | Keyword (`elegant`/`casual`) + `WardrobeAgent.find_replacement()`. Agent retained per `AGENTS.md`. |
| `MemoryAgent` | `agents/memory_agent.py` | No | **SHOULD BE SERVICE** — `update_memory_from_plan()` is deterministic |
| `WardrobeAgent` | `agents/wardrobe_agent.py` | No | **SHOULD BE SERVICE** — scoring/search is deterministic |
| `ShoppingAgent` | `agents/shopping_agent.py` | No | **SHOULD BE SERVICE** — returns stub message, no functionality |
| `SewingAgent` | `agents/sewing_agent.py` | No | **SHOULD BE SERVICE** — returns stub message |
| `TrendAgent` | `agents/trend_agent.py` | No | **SHOULD BE SERVICE** — returns stub message |
| `Planner` (ABC) | `agents/planners/base.py` | No | Planner interface |
| `RuleBasedPlanner` | `agents/planners/rule_based_planner.py` | No | **SHOULD BE SERVICE** — detector composition; active in prod (`USE_LLM=False`) |
| `LLMPlanner` | `agents/planners/llm_planner.py` | **No (currently)** | Keyword mock; OpenAI code commented out. Disabled in prod. Future: LLM → planner service layer |

**Note:** `USE_LLM = False` in `agents/planner.py` (line 16) — prod path is `RuleBasedPlanner`.

### Related services outside `agents/` (reference)

| Module | LLM? | Note |
|--------|------|------|
| `services/rag_service.py` | No | Keyword retrieval, markdown chunk |
| `wardrobe/wardrobe_service.py` | No | Repository wrapper |
| `memory/memory_store.py` | No | JSON + NLP phrase rules |
| `orchestrator/fashion_orchestrator.py` | No | Agent registry + routing |

### Agents registered in orchestrator vs API path

`FashionOrchestrator` (lines 34–41): MemoryAgent, StylistAgent, InlineEditAgent, WardrobeAgent, SewingAgent, TrendAgent, ShoppingAgent — all registered; outfit flow runs a subset by intent.

---

## Frontend controls

Source: `frontend/index.html`. Clickable / interactive controls.

| Control | Line (approx.) | Behavior |
|---------|----------------|----------|
| Landing «How it works» | — | **Hidden** (TODO Phase 3) |
| Landing «About» | — | **Hidden** (TODO Phase 3) |
| «Open my wardrobe» (nav) | 317 | **API** — `openWardrobe()` → `GET /api/wardrobe/items` |
| «Open my wardrobe» (hero) | 326 | **API** — same |
| «See how it works» | — | **Hidden** (TODO Phase 3) |
| Wardrobe 3D click / Enter-Space | 332, 534–536 | **API** — same |
| Rail Dashboard | — | **Hidden** (TODO Phase 2) |
| Rail Wardrobe | — | **Hidden** (TODO Phase 2) |
| Rail Style me | 360 | **Local** — `focusPrompt()` scroll |
| Rail Profile | — | **Hidden** (TODO Phase 3) |
| Rail Settings | — | **Hidden** (TODO Phase 3) |
| «+ Add item» | — | **Hidden** (TODO Phase 2) |
| Prompt input + Enter | 379 | **API** — `startSession()` → `POST /api/outfits` |
| Prompt send (✦) | 380 | **API** — same |
| Example chips (×5) | 386–390 | **Local** — `usePrompt()` fills text; send required for API |
| Mode: My wardrobe | 394 | **Local** — `setMode()`; `mode` not sent to API |
| Mode: Wardrobe + AI | — | **Hidden** (TODO Phase 1) |
| Mode: AI inspiration | — | **Hidden** (TODO Phase 1) |
| Memory chips | — | **Hidden** (TODO Phase 2) |
| Category pills | 541 (dynamic) | **Local** — filter |
| Color swatches | 544 (dynamic) | **Local** — filter |
| «♥ Saved» | 422 | **Local** — `favorites` Set, no persist |
| Grid card click | 561 | **Local** — detail panel |
| Card ♥ favorite | 563 | **Local** — session-only |
| Empty «Add your first piece» | — | **Hidden** (TODO Phase 2) |
| Detail scrim | 437 | **Local** — close |
| Detail close | 439 | **Local** |
| «Style this piece» | 444 | **API** — fill prompt + `startSession()` |
| «Edit details» | — | **Hidden** (TODO Phase 2) |
| Session scrim / close | 452, 459 | **Local** |
| «↻ Regenerate» | 471 | **API** — `runThinking()` → `POST /api/outfits` |
| «Save outfit» | — | **Hidden** (TODO Phase 2) |
| «Wear today» | — | **Hidden** (TODO Phase 2) |
| Board ⟲ swap | 834 (dynamic) | **API** — `POST /api/outfits/inline-edit` |
| Escape key | 597 | **Local** — close detail/session |

**Board note:** `SLOTS = ["Outerwear","Tops","Bottoms","Shoes"]` (623) — `Accessories` items from API are not shown on board (`applyOutfitResponse` 667–670).

---

## Mock/legacy code to remove

### Production / frontend — removed 2026-07-21

| Item | Status |
|------|--------|
| `AI_CATALOG`, `WHY`, `pickFor()`, `buildOutfit()` | **Removed** |
| Hardcoded memory chips | **Hidden** (TODO Phase 2) |
| Landing wardrobe decoration Unsplash URLs | **Replaced** with CSS placeholders |
| Misleading hybrid/inspiration mode buttons | **Hidden** (TODO Phase 1) |
| Non-functional nav/rail/detail/session buttons | **Hidden** (TODO Phase 2–3) |

### Backend agents / planner

| File:Line | Type | Description |
|-----------|------|-------------|
| `agents/stylist_agent.py:19–32` | **hardcoded** | `DEFAULT_ITEMS` — fallback outfit pieces when wardrobe empty/category missing |
| `agents/stylist_agent.py:111` | **hardcoded** | `DEFAULT_ITEMS` usage |
| `agents/planners/llm_planner.py:7,40,53–54` | **mock** | Mock LLM planner (disabled in prod) |
| `agents/planners/__init__.py:7` | **placeholder** | LLMPlanner description |
| `agents/shopping_agent.py:8,22–25` | **placeholder** | Stub agent message |
| `agents/sewing_agent.py:8,22–25` | **placeholder** | Stub agent message |
| `agents/trend_agent.py:8,22–25` | **placeholder** | Stub agent message |
| `agents/inline_edit_agent.py:21` | **legacy** | «legacy dict» context path |
| `api/main.py:45–51` | **hardcoded** | `CATEGORY_IMAGES` — category placeholder when item has no `image_url` |
| `api/main.py:42–43,91` | **hardcoded** | `DEFAULT_EVENT`, `DEFAULT_USER_ID` |
| `tools/weather_tool.py:3` | **mock / unused** | «Mock weather tool» — **not imported by any API route, orchestrator, or agent** (repo-wide grep 2026-07-21). Retained for future weather integration. |

### Streamlit (parallel UI, outside API)

| File | Note |
|------|------|
| `app.py` | Legacy Streamlit UI; uses same orchestrator as FastAPI frontend |

### Test-only mock (do not delete, documented)

| Location | Note |
|----------|------|
| `tests/test_*.py` | `unittest.mock` patch/MagicMock — test infrastructure |

**TODO/FIXME:** Repo-wide `TODO`/`FIXME` search — **no matches**.

---

## Test coverage

| File | What is tested (one line) |
|------|---------------------------|
| `tests/test_api.py` | FastAPI health, wardrobe list, outfit POST, inline-edit POST, serializer helpers |
| `tests/test_agent_context.py` | StylistAgent/InlineEditAgent/Orchestrator wardrobe+memory+RAG flow via `AgentContext` |
| `tests/test_wardrobe_repository.py` | JSON repo CRUD read; StylistAgent/Orchestrator repository fallback |
| `tests/test_sqlite_wardrobe_repository.py` | SQLite schema, CRUD, user isolation, connection commit/rollback |
| `tests/test_repository_factory.py` | Factory JSON/SQLite selection, env override, invalid backend |
| `tests/test_wardrobe_service.py` | WardrobeService delegation |
| `tests/conftest.py` | Shared fixtures (AgentContext, Plan, disk wardrobe) |
| `test_rag.py` (root) | RagService keyword retrieval manual script |
| `test_deneme.py` (root) | Streamlit smoke (`st.write`) — ? outside prod test suite |

### Missing test areas (important)

- Frontend/E2E: **none**
- `POST /api/outfits` mode/source/owned contract: **none** (not yet implemented)
- Assertion that **other items unchanged** after inline edit: **none**
- `GET /api/memory`: endpoint missing
- Hybrid/inspiration mode distinction: **none**
- HTTP status codes on API errors (orchestrator exception): **?**
- `buildOutfit`/`AI_CATALOG` dead code regression: **none**

---

## AGENTS.md compliance summary (current vs target)

| Target (`AGENTS.md`) | Current state |
|----------------------|---------------|
| 3 modes (`my_wardrobe` / `wardrobe_plus_ai` / `ai_inspiration`) | **Missing** — frontend UI exists, backend/API does not |
| `source` + `owned` on every item | **Missing** |
| Mode 1 enforce outside wardrobe | **Missing** — StylistAgent may use `DEFAULT_ITEMS` fallback |
| Mode 2 max 2 suggested | **Missing** |
| Only 2 agents | **Mismatch** — 7 agent classes + planner; 4 are stubs |
| Memory/Wardrobe/Shopping = service | **Partial** — WardrobeService exists; Memory/Wardrobe still agent + manager |
| LLM + Pydantic validation | **Missing** — rule-based planner + keyword RAG |
| No auth, user_id in model | **Partial** — serializer `user_id: "default"` |

---

## Priority findings (short)

1. **`AGENTS.md` contract** — `source`/`owned`/mode enforcement not yet implemented  
2. **Accessories** can be generated in outfit, not shown on board  
3. **Backend mock/legacy** — `DEFAULT_ITEMS`, stub agents, LLMPlanner mock (deferred; agents not touched in cleanup pass)  
