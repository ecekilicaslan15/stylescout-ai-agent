# StyleScout — Architecture Decision Records

| Date | Decision | Context | Rationale | Alternatives |
|------|----------|---------|-----------|--------------|
| 2026-07-21 | Stay on vanilla JS | Frontend technology choice | Portfolio thesis is backend/AI focused; React/Next.js migration costs 2–4 weeks and expands MVP scope | React + Vite, Next.js App Router |
| 2026-07-21 | Agent count reduced from 6 to 2 | Orchestrator and module boundaries | Modules that do not perform reasoning should be deterministic services, not agents; only StylistAgent and InlineEditAgent remain | Keep the existing multi-agent registry |
| 2026-07-21 | Shopping = deep-link, no demo catalog | Shopping / gap-fill feature | No Vinted public buyer API; scraping violates ToS; fake price/stock is a portfolio risk | Mock product catalog, affiliate API integration |
| 2026-07-21 | No auth in MVP | Deployment and multi-tenancy | Single-tenant demo is sufficient; fast deploy; however `user_id` is kept ready on all records in the model | JWT + login, magic link, session cookie |
| 2026-07-21 | Rule-based composer is retained as deterministic fallback | `USE_LLM` was False in production | Gives the system a reliability layer instead of dead code | Remove rule-based path; LLM-only outfit generation |
| 2026-07-21 | All project documentation is written in English | Documentation language policy | Portfolio audience | Mixed TR/EN docs, Turkish-only docs |
| 2026-07-21 | Remove frontend mock/dead code and hide non-functional UI | Audit cleanup pass (`docs/AUDIT.md`) | Visible controls must do something real; mock catalog and dead outfit builder misled users and bypassed the API | Keep mock UI until backend modes ship |
| 2026-07-21 | Docker deployment with SQLite + idempotent seed | Cloud hosting requirement | Single `python:3.11-slim` image, non-root user, `PORT` read at runtime for PaaS compatibility; empty-table seed from `wardrobe.json` recovers ephemeral free-tier filesystems without duplicating data on restart | docker-compose + nginx, bind-mount JSON wardrobe, persistent volume only |
