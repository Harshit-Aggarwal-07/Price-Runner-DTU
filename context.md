# Context — DTU Grocery Price Compare

> **Living document.** Updated as decisions are made.
> **Last updated:** 2026-09-12 03:12 IST

## Project Phase

- [x] Assignment extraction & understanding
- [x] Requirements interview (grill-me) — 15 questions completed
- [x] Multi-agent architecture deliberation (LLM-1)
- [x] LLM-2 analysis received (Node.js + Playwright approach)
- [x] LLM-3 analysis received (DX/Evaluator Impression approach)
- [x] Feature deep-dive (matching types, unit pricing, SSE, coupons)
- [x] Smart Cart analysis (optimizer, delivery costs, ratings)
- [x] Architecture merged & finalized (architecture.md)
- [x] PRD finalized (prd.md)
- [x] SOLID + HLD/LLD critique completed
- [/] Implementation planning
- [ ] Implementation (Phase 1 → Phase 2 → Phase 3)
- [ ] Design note authoring
- [ ] Screen recording

---

## Final Decisions Log

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| D1 | **Python FastAPI + Vanilla JS** | 2/3 LLMs chose Python. Best matching/data ecosystem. FastAPI async for parallel scraping. Vanilla JS = zero build step. | ✅ Final |
| D2 | **Hexagonal Architecture (Ports & Adapters)** | Clean domain core isolation. Adding new platforms = new adapter file only (OCP). | ✅ Final |
| D3 | **Direct HTTP + Fixture Fallback** (not Playwright) | LLM-3 argument decisive: "headless browser for read-only catalog search is overkill." Direct desktop web requests + offline fixtures for evaluator reliability. | ✅ Final |
| D4 | **4-layer hybrid matching with Strategy pattern** | Extract → Hard gate (brand+weight) → Soft match → Confidence score. Multiple strategies available for debug view. | ✅ Final |
| D5 | **In-memory TTL cache (5 min)** | Responsible scraping. Redis mentioned as scale path. | ✅ Final |
| D6 | **Smart Cart with split optimizer** | Differentiator. 2^N brute force for ≤20 items. Delivery cost factored in. | ✅ Final |
| D7 | **MRP + Selling Price (not cart-level coupons)** | Platform discounts scrapable. Cart-level coupons are user-specific — show as manual toggle only. | ✅ Final |
| D8 | **Unit price normalization (₹/100g)** | Must-have. All 3 LLMs rated 10/10 impression. | ✅ Final |
| D9 | **SSE for real-time updates** | Phase 3 extra. 3-min polling, change detection, push notifications. | ✅ Final (P3) |
| D10 | **Local-only, one-command setup** | `pip install -r requirements.txt && python main.py` or `start.bat` | ✅ Final |

---

## Key Documents

| Document | Path | Status |
|----------|------|--------|
| Assignment Brief | `assignment_brief.md` (artifacts) | ✅ Complete |
| Context (this file) | `context.md` (workspace) | ✅ Current |
| **Architecture** | **`architecture.md`** (workspace) | ✅ **FINAL** |
| **PRD** | **`prd.md`** (workspace) | ✅ **FINAL** |
| Deliberation (LLM-1) | `deliberation.md` (artifacts) | ✅ Complete |
| LLM-2 Analysis | `architecture_analysis.md` (workspace) | ✅ Complete |
| LLM-3 Analysis | `llm3_analysis.md` (workspace) | ✅ Complete |
| Feature Deep-Dive | `feature_deep_dive.md` (artifacts) | ✅ Complete |
| Smart Cart Analysis | `smart_cart_analysis.md` (artifacts) | ✅ Complete |
| LLM-2 Handoff Prompt | `llm2_handoff_prompt.md` (workspace) | ✅ Complete |
| LLM-3 Handoff Prompt | `llm3_handoff_prompt.md` (workspace) | ✅ Complete |
| Implementation Plan | `implementation_plan.md` (artifacts) | ⏳ Next |

---

## Tech Stack (Final)

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Python + FastAPI | 3.12.5 |
| HTTP Client | httpx (async) | Latest |
| Data Validation | Pydantic v2 | Latest |
| Frontend | Vanilla HTML/CSS/JS | N/A |
| Caching | cachetools (TTLCache) | Latest |
| Fuzzy Matching | difflib (stdlib) | Built-in |
| Testing | pytest + pytest-asyncio | Latest |
| Server | Uvicorn | Latest |

## Feature Phases

### Phase 1 — Core (MUST be flawless)
- [F1] Search across platforms
- [F2] Product matching (hybrid, multi-strategy)
- [F3] Price comparison with winner badge
- [F4] Unit price normalization (₹/100g)
- [F5] MRP vs selling price display
- [F6] Stock status awareness
- [F7] Deep-link "Buy on X" buttons
- [F8] Skeleton loading states
- [F9] Graceful error handling
- [F10] Fixture fallback mode

### Phase 2 — Smart Cart (Differentiator)
- [F11] Cart builder (add/remove items)
- [F12] Cart totals per platform
- [F13] Split-cart optimizer
- [F14] Delivery cost factor
- [F15] Recommendation engine

### Phase 3 — Extras (If time permits)
- [F16] Matching strategy debug view
- [F17] Coupon awareness (manual toggle)
- [F18] Rating aggregation
- [F19] SSE real-time updates
- [F20] Search history (localStorage)
