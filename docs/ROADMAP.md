# StyleScout — 3-Week MVP Roadmap

## Week 1 — Mode end-to-end + source labelling + validation gate + live URL

| Day | Focus |
|-----|-------|
| Mon | `my_wardrobe` / `wardrobe_plus_ai` / `ai_inspiration` API contract; Pydantic models (`source`, `owned`) |
| Tue | Mode 1 enforcement: no items outside wardrobe returned (deterministic gate, not left to prompt) |
| Wed | Mode 2: suggested item cap (max 2); Mode 3: ideal outfit → ownership resolver flow |
| Thu | Frontend: mode selector wired to real backend; fake hybrid/inspiration UI removed |
| Fri | Validation gate: LLM output → repair (1x) → deterministic fallback; tests |
| Sat | Deploy pipeline (uvicorn + static); live URL; README update |
| Sun | Buffer / bugfix; begin filling `docs/AUDIT.md` endpoints section |

**Week 1 acceptance criteria**
- [ ] Three modes produce genuinely different results via POST `/api/outfits`
- [ ] Every outfit item has `source` and `owned` fields
- [ ] Mode 1: no response item carries `source: "suggested"`
- [ ] Live URL: prompt → outfit → inline edit works
- [ ] All tests pass; related decisions appended to `docs/DECISIONS.md`

---

## Week 2 — Wardrobe CRUD + session persistence + inline edit + shopping deep-link

| Day | Focus |
|-----|-------|
| Mon | `POST /api/wardrobe/items` + add-item form (frontend module) |
| Tue | Session persistence: active outfit state (localStorage or backend session) |
| Wed | Inline edit: free-text instruction UI; swap button sends full instruction to API |
| Thu | `search_spec` model + ShoppingService (deep-link URL generation, no scraping) |
| Fri | DeepLinkProvider (marketplace search URLs); links on Mode 2 suggested items |
| Sat | `GET /api/memory` read + memory chips rendered from real data |
| Sun | Buffer; wardrobe SQLite optional switch documentation |

**Week 2 acceptance criteria**
- [ ] User can add wardrobe items from UI; grid updates
- [ ] Last outfit session can be restored after page refresh
- [ ] Inline edit accepts user text (not only elegant/casual toggle)
- [ ] Mode 2 suggested items have real marketplace deep-links (no fake prices)
- [ ] Memory chips read from backend

---

## Week 3 — Explanation panel + eval + portfolio package + final deploy

| Day | Focus |
|-----|-------|
| Mon | Explanation panel: plan, reason, stylist_notes, mode-aware copy |
| Tue | Eval harness: fixed prompt set + mode/source/owned assertions |
| Wed | Full `docs/AUDIT.md` update; mock/legacy code cleanup list applied |
| Thu | README + architecture diagram (orchestrator → services → agents) |
| Fri | Demo video script / recording; portfolio README polish |
| Sat | Final deploy; smoke test checklist |
| Sun | Buffer; retrospective + `docs/DECISIONS.md` summary |

**Week 3 acceptance criteria**
- [ ] Explanation panel shows plan and rationale after outfit generation
- [ ] Eval harness automatically validates at least 10 scenarios
- [ ] `docs/AUDIT.md` is current; known fake UI controls marked or removed
- [ ] README includes deploy + architecture + demo link
- [ ] Production URL stable; tests green
