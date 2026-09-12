# PRD — DTU Grocery Price Compare
## "The Great DTU Grocery Race"

> **Version:** 1.0
> **Author:** [Your Name]
> **Date:** 2026-09-12
> **Status:** Approved for Implementation

---

## 1. Problem Statement

DTU hostel residents (our users) need to compare grocery prices across Blinkit and Instamart before ordering at night. Currently this requires opening two apps, searching twice, and mentally comparing prices — a frustrating process that leads to suboptimal purchasing decisions.

## 2. Target User

**Primary Persona:** DTU hostel student, 11 PM, hungry, budget-conscious.
- Wants the cheapest option for their grocery items
- Orders 3-10 items at a time (not just one)
- Cares about: price, stock availability, delivery cost, speed
- Does NOT care about: architecture, tech stack, code quality (that's the evaluator)

## 3. Core Value Proposition

> **One search. Both platforms. Best deal. Optimized cart.**

## 4. Feature Specification

### Phase 1 — Core (Must ship perfectly)

| ID | Feature | User Story | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F1 | **Search** | As a user, I search for "Maggi" and see results from both platforms | Results from Blinkit + Instamart appear in < 5s |
| F2 | **Product Matching** | As a user, I see which products are the same across platforms | Matched pairs shown with confidence score |
| F3 | **Price Comparison** | As a user, I see which platform is cheaper | Clear "winner" badge with ₹ difference |
| F4 | **Unit Price** | As a user, I see ₹/100g to compare different pack sizes | Unit price shown for all products with weight info |
| F5 | **MRP vs Selling** | As a user, I see the discount each platform offers | MRP (strikethrough) + selling price + discount % |
| F6 | **Stock Status** | As a user, I see if an item is in stock at DTU | Clear in-stock / out-of-stock badge |
| F7 | **Deep Links** | As a user, I click "Buy on Blinkit" to go directly there | Button opens product page in new tab |
| F8 | **Skeleton Loading** | As a user, I see something happening while results load | Skeleton cards animate during fetch |
| F9 | **Graceful Errors** | As a user, I still see results if one platform is down | Partial results + "Platform unavailable" banner |
| F10 | **Fixture Fallback** | As an evaluator, the app works even if scraping fails | Toggle to "Offline Snapshot Mode" |

### Phase 2 — Smart Cart (The Differentiator)

| ID | Feature | User Story | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F11 | **Cart Builder** | As a user, I add multiple items to compare as a bundle | "Add to Cart" button on each matched pair |
| F12 | **Cart Totals** | As a user, I see total cost on each platform | "All from Blinkit: ₹487, All from Instamart: ₹462" |
| F13 | **Split Optimizer** | As a user, I see the cheapest combination including delivery | "Buy items 1,3 from Blinkit + item 2 from Instamart = ₹431" |
| F14 | **Delivery Cost** | As a user, delivery fees are factored into the recommendation | Free delivery thresholds applied correctly |
| F15 | **Recommendation** | As a user, I get a clear recommendation with reasoning | "Order everything from Instamart. Split saves only ₹3 — not worth 2 deliveries." |

### Phase 3 — Extras (If Time Permits)

| ID | Feature | User Story |
|----|---------|-----------|
| F16 | **Matching Debug View** | As an evaluator, I toggle to see all matching strategy scores |
| F17 | **Coupon Awareness** | As a user, I see how coupons could affect my total |
| F18 | **Rating Aggregation** | As a user, I see combined ratings from both platforms |
| F19 | **SSE Real-Time Updates** | As a user, I get notified if prices/stock change while browsing |
| F20 | **Search History** | As a user, I see my recent searches (localStorage) |

## 5. Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Response Time** | < 5 seconds for search results | User abandonment threshold |
| **Setup Time** | < 60 seconds on evaluator's fresh machine | Evaluator is reviewing 50+ submissions |
| **Uptime** | Graceful degradation, never crash | Professional engineering |
| **Scraping Ethics** | Cache results for 5 min, max 1 req/platform/search | Respect source sites |
| **Browser Support** | Chrome (latest) | Sufficient for localhost demo |
| **Code Readability** | Self-documenting, type-hinted, modular | Evaluator reads code |

## 6. Success Metrics (for Design Note)

1. **Does the app answer "Is this cheaper on Blinkit or Instamart?" in one search?** → YES
2. **Can the evaluator run it in < 60 seconds?** → YES (one-command setup)
3. **Is the matching logic explained and honest about failures?** → YES (5-stage pipeline + failure cases)
4. **Does the scalability discussion show depth?** → YES (location partitioning, worker pools, cache key design)
5. **Does the submission stand out?** → YES (cart optimizer, unit pricing, matching strategy comparison)

## 7. Out of Scope

- User authentication / accounts
- Mobile app
- Deployment to production
- Support for platforms beyond Blinkit + Instamart (architecture supports it, but not implemented)
- Cart-level coupon auto-application (shown as manual toggle only)
- Price history tracking (requires persistent data collection)

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Scraping breaks during eval | App shows no data | Fixture fallback mode (F10) |
| Product matching is inaccurate | Wrong price comparisons | Confidence scores + honest failure documentation |
| Setup fails on evaluator machine | Submission rejected | One-click scripts + zero C-extension deps |
| Scope creep (too many features) | Core doesn't work perfectly | Strict phase discipline: P1 must be flawless before P2 |
