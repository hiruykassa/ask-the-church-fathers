# Walkthrough — owning this project end to end

This folder is a self-study course for the **Ask the Early Church** codebase. It is written for someone who wants to understand the project deeply enough to own it, extend it, and explain it in a fullstack-plus-AI interview in 2026.

Each file teaches one slice of the system: first the **concept** (the transferable skill), then the **code** (the important and tricky lines, with file references).

## Reading order

| # | Module | Transferable skill |
|---|--------|--------------------|
| 01 | [Orientation & mental model](01-orientation.md) | System architecture, request lifecycle |
| 02 | [Running it / dev environment](02-dev-environment.md) | Local dev setup, secrets hygiene |
| 03 | [Data layer](03-data-layer.md) | Relational modeling + full-text search (SQLite/FTS5) |
| 04 | [Backend setup & security](04-backend-security.md) | Production API hardening |
| 05 | [Search engine part 1 — embeddings & query understanding](05-search-embeddings.md) | Embeddings, RAG inputs, caching, cost control |
| 06 | [Search engine part 2 — hybrid ranking](06-search-ranking.md) | Hybrid semantic + keyword search, graceful degradation |
| 07 | [Remaining backend endpoints](07-backend-endpoints.md) | REST resource design |
| 08 | [Frontend foundation](08-frontend-foundation.md) | React state, routing, custom hooks |
| 09 | [Frontend pages & components](09-frontend-pages.md) | Component composition, safe rendering |
| 10 | [Offline corpus pipeline](10-corpus-pipeline.md) | ETL / data pipelines for AI |
| 11 | [SEO, build & deploy, CI](11-deploy-ci.md) | Build pipeline, containers, cloud deploy, CI/CD |
| 12 | [Ownership & interview prep](12-ownership.md) | Communicating architecture |
| 13 | [Maintenance mode & known issues](13-maintenance.md) | Operating a finished system; honest defect triage |

## How to use this

Modules 01–12 are a course: read them in order. **Module 13 is a reference** — skim it once so you know what's in it, then return to it whenever you're about to change the corpus or ship a deploy. It's also where the project's known defects are recorded honestly, which is the part worth reading before an interview asks "what would you do differently?"

Read a module, then open the real file beside it and trace the lines. The line references look like `backend/app.py:164` — jump there and confirm what the guide says against the live code. When something changes in the code, update the matching note here.
