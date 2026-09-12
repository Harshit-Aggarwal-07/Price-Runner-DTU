# Architecture — DTU Grocery Price Compare

> **Version:** 1.0 (Merged from 3 independent LLM analyses + feature deep-dives)
> **Last Updated:** 2026-09-12 03:07 IST
> **Status:** Final Draft — Pre-Implementation

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Design (HLD)](#2-high-level-design)
3. [Low-Level Design (LLD)](#3-low-level-design)
4. [Design Patterns & Principles](#4-design-patterns--principles)
5. [SOLID Principles Critique](#5-solid-principles-critique)
6. [HLD/LLD Principles Critique](#6-hldlld-principles-critique)
7. [Data Models](#7-data-models)
8. [API Contracts](#8-api-contracts)
9. [Product Matching Engine (Deep Dive)](#9-product-matching-engine)
10. [Smart Cart & Optimizer](#10-smart-cart--optimizer)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Scalability Analysis](#12-scalability-analysis)
13. [Tech Stack Decision (Merged Verdict)](#13-tech-stack-decision)
14. [Project Structure](#14-project-structure)
15. [Rejected Alternatives](#15-rejected-alternatives)

---

## 1. System Overview

### What It Is
A grocery price comparison web app that lets DTU hostel residents search for items and compare prices across Blinkit and Instamart in a single search, with a smart cart optimizer that recommends the cheapest way to order.

### Core Value Proposition
```
Single item search → Compare across platforms → Add to cart → 
Smart optimizer says: "Order items 1,3 from Blinkit + item 2 from Instamart = 
₹431 total (saves ₹31 vs all from one platform)"
```

### Architecture Philosophy
- **Customer-first:** Every architectural decision traces back to "what does the DTU student at 11 PM need?"
- **Modular & extensible:** Adding Zepto, BigBasket, or JioMart should require only a new adapter file
- **Honest over perfect:** Show confidence scores, acknowledge limitations, degrade gracefully
- **Simple to run:** `pip install -r requirements.txt && python main.py` — done

---

## 2. High-Level Design

### 2.1 System Context Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER (DTU Student)                            │
│                     Browser @ localhost:8000                          │
└──────────────────────┬────────────────────────────┬──────────────────┘
                       │ HTTP REST                  │ SSE (Phase 3)
                       ▼                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       APPLICATION SERVER                             │
│                     FastAPI (Python 3.12)                             │
│                                                                      │
│  ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Search  │  │ Cart         │  │ Cache    │  │ Platform         │  │
│  │ API     │  │ Optimizer    │  │ Layer    │  │ Registry         │  │
│  └────┬────┘  └──────┬───────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │               │                  │            │
│       ▼              ▼               ▼                  ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    ORCHESTRATOR (async)                          │ │
│  │              asyncio.gather → parallel platform fetch           │ │
│  └──────────────────────────┬──────────────────────────────────────┘ │
│                             │                                        │
│              ┌──────────────┼──────────────┐                         │
│              ▼              ▼              ▼                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │
│  │ Blinkit       │ │ Instamart     │ │ [Future]      │              │
│  │ Adapter       │ │ Adapter       │ │ Zepto/BB/Jio  │              │
│  │ (implements   │ │ (implements   │ │ Adapter       │              │
│  │ PlatformPort) │ │ PlatformPort) │ │               │              │
│  └───────┬───────┘ └───────┬───────┘ └───────────────┘              │
│          │                 │                                         │
│          ▼                 ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                 DOMAIN CORE (Pure Business Logic)               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │ │
│  │  │ Normalizer   │  │ Matcher      │  │ Cart Optimizer        │ │ │
│  │  │ (extract     │  │ (multi-stage │  │ (split-cart algo,     │ │ │
│  │  │  brand/wt/   │  │  pipeline,   │  │  delivery costs,     │ │ │
│  │  │  unit)       │  │  confidence) │  │  recommendations)    │ │ │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                       │                 │
                       ▼                 ▼
            ┌──────────────┐   ┌──────────────┐
            │ blinkit.com  │   │ swiggy.com/  │
            │              │   │ instamart    │
            └──────────────┘   └──────────────┘
```

### 2.2 Component Breakdown

| Component | Responsibility | Layer |
|-----------|---------------|-------|
| **Search API** | Accepts query, orchestrates fetch+match, returns results | Interface (API) |
| **Cart Optimizer API** | Accepts cart items, computes optimal assignment | Interface (API) |
| **Platform Registry** | Discovers & manages registered platform adapters | Application |
| **Orchestrator** | Parallel-dispatches search to all registered adapters | Application |
| **Cache Layer** | TTL cache keyed by `(query, location)` | Infrastructure |
| **PlatformPort** (Interface) | Abstract contract for any grocery platform | Domain Port |
| **Blinkit Adapter** | Implements PlatformPort for Blinkit | Infrastructure (Adapter) |
| **Instamart Adapter** | Implements PlatformPort for Instamart | Infrastructure (Adapter) |
| **Normalizer** | Extracts brand, weight, unit from raw product names | Domain Core |
| **Matcher** | Multi-stage product matching with confidence scoring | Domain Core |
| **Cart Optimizer** | Split-cart algorithm with delivery cost optimization | Domain Core |

### 2.3 Data Flow (Search)

```
1. User types "Maggi" in search bar
2. Frontend debounces (350ms), sends GET /api/search?q=maggi
3. Backend checks cache → miss
4. Orchestrator dispatches to all registered adapters in parallel
   → BlinkitAdapter.search("maggi", location=DTU)
   → InstamartAdapter.search("maggi", location=DTU)
5. Each adapter returns List[RawListing] (platform-specific format)
6. Normalizer standardizes each listing → List[NormalizedProduct]
7. Matcher runs cross-platform matching → MatchResult
   (matched_pairs + blinkit_only + instamart_only)
8. Response cached with 5-min TTL
9. JSON response returned to frontend
10. Frontend renders comparison cards
```

### 2.4 Data Flow (Cart Optimization)

```
1. User adds matched products to cart (frontend localStorage)
2. User clicks "Optimize Cart"
3. Frontend sends POST /api/cart/optimize with cart items + quantities
4. Backend runs split-cart algorithm:
   a. For each 2^N assignment (brute-force if N ≤ 20, greedy otherwise):
      - Sum item costs per platform
      - Add delivery costs (free above threshold, else base fee)
      - Track minimum total
   b. Compare: all-Blinkit vs all-Instamart vs optimal-split
5. Return recommendation with reasoning
```

---

## 3. Low-Level Design

### 3.1 Hexagonal Architecture (Ports & Adapters)

We use **Hexagonal Architecture** (also called Ports & Adapters) to ensure the domain core is completely isolated from external dependencies.

```
                    ┌──────────────────────────────────┐
                    │         DRIVING SIDE             │
                    │    (Primary / Input Ports)        │
                    │                                  │
                    │  ┌──────────────────────────┐    │
                    │  │  SearchPort               │    │
                    │  │  + search(q, loc) → Result│    │
                    │  └──────────────────────────┘    │
                    │  ┌──────────────────────────┐    │
                    │  │  CartPort                 │    │
                    │  │  + optimize(cart) → Rec   │    │
                    │  └──────────────────────────┘    │
                    │              │                    │
          ┌─────────┴──────────────┴────────────────┐  │
          │            DOMAIN CORE                   │  │
          │  (Pure business logic, zero dependencies)│  │
          │                                          │  │
          │  Normalizer  │  Matcher  │  CartOptimizer │  │
          │                                          │  │
          └─────────┬──────────────┬─────────────────┘  │
                    │              │                     │
                    │         DRIVEN SIDE                │
                    │    (Secondary / Output Ports)      │
                    │                                    │
                    │  ┌──────────────────────────┐     │
                    │  │  PlatformPort (ABC)       │     │
                    │  │  + search(q, loc)→ [Raw]  │     │
                    │  │  + get_delivery_info()    │     │
                    │  │  + get_product_url(id)    │     │
                    │  └──────────────────────────┘     │
                    │  ┌──────────────────────────┐     │
                    │  │  CachePort (ABC)          │     │
                    │  │  + get(key) → data | None │     │
                    │  │  + set(key, data, ttl)    │     │
                    │  └──────────────────────────┘     │
                    └──────────────────────────────────┘

Adapters (Infrastructure):
  PlatformPort ← BlinkitAdapter, InstamartAdapter, [ZeptoAdapter, ...]
  CachePort    ← MemoryCacheAdapter, [RedisCacheAdapter, ...]
  SearchPort   ← FastAPISearchController (HTTP)
  CartPort     ← FastAPICartController (HTTP)
```

### 3.2 Class Diagram

```
┌─────────────────────────────────────────────────────┐
│                    «abstract»                        │
│                  PlatformPort                        │
├─────────────────────────────────────────────────────┤
│ + platform_name: str                                │
│ + platform_id: str                                  │
│ + base_url: str                                     │
├─────────────────────────────────────────────────────┤
│ + search(query: str, location: Location)            │
│     → list[RawListing]                «abstract»    │
│ + get_delivery_info(location: Location)             │
│     → DeliveryInfo                    «abstract»    │
│ + get_product_url(product_id: str)                  │
│     → str                             «abstract»    │
│ + health_check() → bool              «abstract»    │
└───────────────┬─────────────────────┬───────────────┘
                │                     │
    ┌───────────▼──────┐  ┌──────────▼────────┐
    │ BlinkitAdapter    │  │ InstamartAdapter   │
    ├──────────────────┤  ├───────────────────┤
    │ - _client: httpx │  │ - _client: httpx  │
    │ - _headers: dict │  │ - _headers: dict  │
    ├──────────────────┤  ├───────────────────┤
    │ + search(...)    │  │ + search(...)     │
    │ + _parse_resp()  │  │ + _parse_resp()   │
    └──────────────────┘  └───────────────────┘

┌────────────────────────────────────────────────┐
│                  Normalizer                     │
├────────────────────────────────────────────────┤
│ - _brand_aliases: dict[str, str]               │
│ - _unit_conversions: dict[str, float]          │
│ - _weight_pattern: re.Pattern                  │
├────────────────────────────────────────────────┤
│ + normalize(raw: RawListing) → NormalizedProduct│
│ + extract_brand(name: str) → str               │
│ + extract_weight(name: str) → WeightInfo       │
│ + compute_unit_price(price, weight) → float    │
│ - _clean_name(name: str) → str                 │
│ - _expand_multipack(name: str) → float         │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                     Matcher                             │
├────────────────────────────────────────────────────────┤
│ - _strategies: list[MatchingStrategy]                  │
│ - _default_strategy: str                               │
│ - _confidence_threshold: float                         │
├────────────────────────────────────────────────────────┤
│ + match(a: list[NormProduct], b: list[NormProduct])    │
│     → MatchResult                                      │
│ + match_with_strategy(a, b, strategy: str)             │
│     → MatchResult                                      │
│ - _compute_confidence(a: NormProduct, b: NormProduct)  │
│     → float                                            │
│ - _hard_gate(a, b) → bool                              │
│ - _soft_score(a, b) → float                            │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                «abstract»                               │
│              MatchingStrategy                           │
├────────────────────────────────────────────────────────┤
│ + strategy_name: str                                   │
│ + compute_similarity(a: NormProduct, b: NormProduct)   │
│     → float                             «abstract»     │
└──────┬──────────┬────────────┬────────────┬────────────┘
       │          │            │            │
  ExactMatch  TokenSetRatio  Levenshtein  HybridGated
  Strategy    Strategy       Strategy     Strategy
```

### 3.3 Sequence Diagram (Search Flow)

```
User        Frontend       SearchAPI      Cache     Orchestrator    BlinkitAdapter    InstamartAdapter    Normalizer    Matcher
 │              │              │            │            │                │                  │                │            │
 │─ type ──────▶│              │            │            │                │                  │                │            │
 │              │─ debounce ──▶│            │            │                │                  │                │            │
 │              │  GET /search │            │            │                │                  │                │            │
 │              │──────────────▶│           │            │                │                  │                │            │
 │              │              │── get() ──▶│            │                │                  │                │            │
 │              │              │◄── miss ───│            │                │                  │                │            │
 │              │              │── dispatch ────────────▶│                │                  │                │            │
 │              │              │            │            │── search() ───▶│                  │                │            │
 │              │              │            │            │── search() ────────────────────  ▶│                │            │
 │              │              │            │            │                │                  │                │            │
 │              │              │            │            │◄─ [RawListing] │                  │                │            │
 │              │              │            │            │◄─ [RawListing] ──────────────────│                │            │
 │              │              │            │            │                                                   │            │
 │              │              │            │            │── normalize(blinkit_raw) ────────────────────────▶│            │
 │              │              │            │            │── normalize(instamart_raw) ─────────────────────▶│            │
 │              │              │            │            │◄─ [NormalizedProduct] ───────────────────────────│            │
 │              │              │            │            │                                                                │
 │              │              │            │            │── match(blinkit_norm, instamart_norm) ─────────────────────────▶│
 │              │              │            │            │◄─ MatchResult ────────────────────────────────────────────────│
 │              │              │            │            │                │                  │                │            │
 │              │              │◄───────────────────────│                │                  │                │            │
 │              │              │── set() ──▶│            │                │                  │                │            │
 │              │◄─ JSON ──────│            │            │                │                  │                │            │
 │◄── render ──│              │            │            │                │                  │                │            │
```

---

## 4. Design Patterns & Principles

### Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| **Strategy** | `MatchingStrategy` (Exact, TokenSet, Levenshtein, Hybrid) | Swap matching algorithms without changing matcher. Enables debug view showing all strategies. |
| **Adapter** | `BlinkitAdapter`, `InstamartAdapter` | Isolates platform-specific scraping logic. Adding a new platform = adding a new adapter file. |
| **Port/Interface** | `PlatformPort`, `CachePort` | Defines contracts without coupling to implementations. Enables testing with mocks. |
| **Registry** | `PlatformRegistry` | Auto-discovers and manages adapters. Adding Zepto = register one class, zero other changes. |
| **Template Method** | `BasePlatformAdapter._fetch_and_parse()` | Common HTTP logic (headers, retries, timeout) in base; platform-specific parsing in subclass. |
| **Factory** | `PlatformRegistry.create_adapter()` | Construct adapters from config without client code knowing concrete types. |
| **Observer** | SSE event stream (Phase 3) | Frontend subscribes to price/stock changes without polling. |
| **Circuit Breaker** | Per-adapter fault tracking | After N failures, skip adapter and serve cached/partial results. |
| **Decorator** | `@cached(ttl=300)` on search methods | Transparent caching without modifying business logic. |
| **Value Object** | `WeightInfo`, `Location`, `UnitPrice` | Immutable domain primitives with built-in validation & comparison. |

### Adding a New Platform (OCP in Practice)

To add Zepto as a new platform, you'd create ONE file:

```python
# adapters/zepto.py

from core.ports import PlatformPort, RawListing, Location, DeliveryInfo

class ZeptoAdapter(PlatformPort):
    platform_name = "Zepto"
    platform_id = "zepto"
    base_url = "https://www.zeptonow.com"
    
    async def search(self, query: str, location: Location) -> list[RawListing]:
        # Zepto-specific fetch + parse logic
        ...
    
    async def get_delivery_info(self, location: Location) -> DeliveryInfo:
        ...
    
    def get_product_url(self, product_id: str) -> str:
        return f"{self.base_url}/product/{product_id}"
    
    async def health_check(self) -> bool:
        ...
```

Then register it:
```python
# config.py
ENABLED_PLATFORMS = ["blinkit", "instamart", "zepto"]  # Just add here
```

**Zero changes to:** Normalizer, Matcher, Cart Optimizer, API layer, Frontend.
That's the Open/Closed Principle.

---

## 5. SOLID Principles Critique

### ✅ S — Single Responsibility Principle

| Component | Single Responsibility | Verdict |
|-----------|----------------------|---------|
| `BlinkitAdapter` | Fetch data from Blinkit ONLY | ✅ Pass |
| `Normalizer` | Extract/clean product fields ONLY | ✅ Pass |
| `Matcher` | Match products across platforms ONLY | ✅ Pass |
| `CartOptimizer` | Optimize cart assignment ONLY | ✅ Pass |
| `SearchAPI` | HTTP request handling ONLY (delegates to orchestrator) | ✅ Pass |
| `Cache` | Cache management ONLY | ✅ Pass |

**Critique:** The `Normalizer` could be argued as having two responsibilities — name cleaning AND weight extraction. If these grow complex independently, split into `NameCleaner` and `WeightParser`. For current scope, keeping them together is pragmatic.

### ✅ O — Open/Closed Principle

| Extension Point | Open For Extension | Closed For Modification |
|----------------|-------------------|------------------------|
| New platform | Add new adapter implementing `PlatformPort` | No changes to orchestrator, matcher, cache |
| New matching strategy | Add new class implementing `MatchingStrategy` | No changes to matcher's coordination logic |
| New cache backend | Add new class implementing `CachePort` | No changes to business logic |
| New API endpoint | Add route in FastAPI | No changes to domain core |

**Critique:** The `Normalizer`'s brand alias dictionary and regex patterns ARE hardcoded. To truly satisfy OCP, these should be loaded from a config file. Recommendation: `config/brand_aliases.json` and `config/weight_patterns.json`.

### ✅ L — Liskov Substitution Principle

Any `PlatformPort` implementation must:
- Accept the same `(query, location)` inputs
- Return `list[RawListing]` (even if empty)
- Raise only declared exceptions (`PlatformError`, `PlatformTimeoutError`)
- Never return `None` (return `[]` instead)

```python
# This MUST work for ANY adapter:
for adapter in registry.get_all_adapters():
    results = await adapter.search("maggi", dtu_location)
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, RawListing)
```

**Critique:** If a future adapter (e.g., BigBasket) returns products without weight info, the `Normalizer` must handle `weight=None` gracefully. The current design assumes weight is extractable — this is a potential LSP violation. Fix: make `weight_value` Optional in `NormalizedProduct`.

### ✅ I — Interface Segregation Principle

```python
# GOOD — separate interfaces for separate concerns
class PlatformPort(ABC):      # Scraping
    search(...)
    health_check(...)

class DeliveryPort(ABC):       # Delivery info (could be separate from product search)
    get_delivery_info(...)
    get_delivery_cost(subtotal)

class ProductLinkPort(ABC):    # Deep linking
    get_product_url(product_id)
```

**Critique:** Currently `PlatformPort` bundles search, delivery info, and product URLs. A platform might support searching but not delivery info (e.g., a price aggregator). Split if needed, but for 2 platforms this is acceptable pragmatism.

**Current design decision:** Keep bundled for now. If we add >3 platforms with varying capabilities, split the interface.

### ✅ D — Dependency Inversion Principle

```python
# HIGH-LEVEL module (Orchestrator) depends on ABSTRACTION (PlatformPort)
class Orchestrator:
    def __init__(self, adapters: list[PlatformPort], cache: CachePort):
        self._adapters = adapters  # Injected, not constructed
        self._cache = cache

# NOT this:
class Orchestrator:
    def __init__(self):
        self._blinkit = BlinkitAdapter()  # ❌ Concrete dependency
        self._instamart = InstamartAdapter()  # ❌
```

**Critique:** Fully satisfied. The domain core has ZERO imports from `adapters/` or `infrastructure/`. All dependencies flow inward via constructor injection.

---

## 6. HLD/LLD Principles Critique

### 6.1 Separation of Concerns

| Layer | Contains | Does NOT Contain |
|-------|----------|-----------------|
| **API (Interface)** | Route definitions, request/response validation, HTTP concerns | Business logic, scraping logic, matching algorithms |
| **Application** | Orchestration, adapter dispatch, caching coordination | HTTP concerns, platform-specific code, algorithms |
| **Domain Core** | Normalizer, Matcher, CartOptimizer, Value Objects | HTTP, database, external service calls |
| **Infrastructure** | Platform adapters, cache implementations, HTTP clients | Business rules, API routes |

✅ **Verdict:** Clean layering. The domain core is a pure Python package with zero external dependencies.

### 6.2 Cohesion & Coupling Analysis

| Component Pair | Coupling Type | Strength | Assessment |
|----------------|--------------|----------|------------|
| API ↔ Orchestrator | Data coupling (passes query/location) | Loose | ✅ Good |
| Orchestrator ↔ Adapters | Interface coupling (via PlatformPort) | Loose | ✅ Good |
| Normalizer ↔ Matcher | Data coupling (NormalizedProduct) | Loose | ✅ Good |
| Adapter ↔ External Site | External coupling (HTTP/DOM) | Tight (unavoidable) | ⚠️ Managed via adapter isolation |
| Frontend ↔ Backend | Contract coupling (JSON API) | Loose | ✅ Good |

**High cohesion within each module:**
- `Normalizer`: All methods relate to name/weight/brand extraction — cohesive
- `Matcher`: All methods relate to cross-platform product comparison — cohesive
- `BlinkitAdapter`: All methods relate to Blinkit data access — cohesive

### 6.3 Fan-In / Fan-Out Analysis

```
Fan-Out (dependencies a component has):
  Orchestrator → [PlatformPort×N, CachePort, Normalizer, Matcher] = 4+ (acceptable)
  SearchAPI → [Orchestrator] = 1 (excellent)
  BlinkitAdapter → [httpx, PlatformPort] = 2 (excellent)
  Matcher → [MatchingStrategy×N] = variable (managed via Strategy pattern)

Fan-In (components that depend on it):
  NormalizedProduct → [Matcher, CartOptimizer, Frontend] = 3 (it's a core data structure, expected)
  PlatformPort → [BlinkitAdapter, InstamartAdapter, +future] = N (expected for an interface)
```

✅ No component has excessive fan-out. The Orchestrator has the highest, which is expected for a coordinator.

### 6.4 Idempotency & Statelessness

| Component | Stateful? | Idempotent? | Notes |
|-----------|-----------|-------------|-------|
| Search API | Stateless | Yes | Same query → same results (modulo cache TTL) |
| Adapters | Stateless | Yes | Purely fetch + parse, no side effects |
| Normalizer | Stateless | Yes | Pure function: same input → same output |
| Matcher | Stateless | Yes | Pure function |
| Cart Optimizer | Stateless | Yes | Pure function |
| Cache | Stateful | N/A | By design — it stores state |
| Cart (Frontend) | Stateful | N/A | Lives in localStorage, by design |

✅ All business logic components are **stateless and idempotent**. Only the cache and frontend cart are stateful, and both are explicit about it.

### 6.5 Failure Domain Isolation

```
Failure in BlinkitAdapter:
  → Does NOT affect InstamartAdapter (independent async tasks)
  → Does NOT crash the server (exception caught by Orchestrator)
  → Partial results returned: "Blinkit unavailable, showing Instamart only"
  → Cached results served if available

Failure in Matcher:
  → Does NOT affect data fetching (already completed)
  → Fallback: return unmatched lists (Blinkit results + Instamart results, no pairing)
  → User sees both lists side-by-side without match badges

Failure in CartOptimizer:
  → Does NOT affect search (independent feature)
  → Fallback: show simple totals without optimization recommendation
```

✅ Each failure domain is **isolated**. No cascading failures.

### 6.6 Testability Assessment

| Component | Unit Testable? | How |
|-----------|---------------|-----|
| Normalizer | ✅ Trivially | Pure function: `assert normalize("Maggi 2-Min 70g").weight == 70` |
| Matcher | ✅ Trivially | Pure function: feed two product lists, assert matches |
| CartOptimizer | ✅ Trivially | Pure function: feed cart + delivery config, assert optimal assignment |
| Adapters | ✅ With mocks | Mock HTTP responses, verify parse logic |
| Orchestrator | ✅ With mocks | Inject mock adapters implementing PlatformPort |
| API | ✅ With TestClient | FastAPI's built-in TestClient, no external deps |

**Test strategy:** Domain core tests run with zero network calls. Adapter tests use recorded fixtures. Integration tests use the offline fixture mode.

---

## 7. Data Models

### 7.1 Core Domain Models

```python
# ── Value Objects (Immutable) ──

@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    label: str = "DTU Campus"
    pincode: str = "110042"

@dataclass(frozen=True)
class WeightInfo:
    value: float          # 70
    unit: str             # "g"
    base_value: float     # 70.0 (normalized to grams or ml)
    base_unit: str        # "g"
    raw_text: str         # "70 g" (original extracted text)
    is_multipack: bool    # True if "Pack of 4 x 70g"
    pack_count: int       # 4 (or 1 if single)

# ── Entities ──

class RawListing(BaseModel):
    """Raw product data as scraped from a platform. Platform-specific."""
    platform: str
    name: str
    price: float
    mrp: float | None = None
    image_url: str | None = None
    product_url: str | None = None
    in_stock: bool = True
    rating: float | None = None
    rating_count: int | None = None
    raw_weight_text: str | None = None    # "70 g", "500 ml", "Pack of 4"
    category: str | None = None

class NormalizedProduct(BaseModel):
    """Cleaned, normalized product ready for matching."""
    platform: str
    raw_name: str                         # Original name
    normalized_name: str                  # Cleaned name
    brand: str | None = None              # Extracted brand
    product_type: str | None = None       # "noodles", "butter", "milk"
    variant: str | None = None            # "masala", "salted", "toned"
    weight: WeightInfo | None = None      # Structured weight
    price: float                          # Selling price
    mrp: float | None = None              # MRP
    discount_pct: float | None = None     # (mrp - price) / mrp * 100
    unit_price: float | None = None       # price / base_weight (₹/100g or ₹/100ml)
    unit_price_label: str | None = None   # "₹20.00/100g"
    in_stock: bool = True
    product_url: str | None = None
    image_url: str | None = None
    rating: float | None = None
    rating_count: int | None = None

# ── Match Results ──

class MatchedPair(BaseModel):
    """Two products from different platforms identified as the same item."""
    canonical_name: str                   # Best name to display
    confidence: float                     # 0.0–1.0
    confidence_label: str                 # "High", "Medium", "Low"
    products: dict[str, NormalizedProduct] # {"blinkit": ..., "instamart": ...}
    cheaper_platform: str | None          # "blinkit" | "instamart" | None (tie)
    price_diff: float                     # Absolute savings
    unit_price_diff: float | None         # Unit price difference
    match_details: dict[str, float]       # Per-strategy scores (for debug view)

class MatchResult(BaseModel):
    """Complete matching output for a search query."""
    query: str
    location: Location
    matched_pairs: list[MatchedPair]
    unmatched: dict[str, list[NormalizedProduct]]  # {"blinkit": [...], "instamart": [...]}
    metadata: SearchMetadata

class SearchMetadata(BaseModel):
    timestamp: datetime
    cache_hit: bool
    fetch_times: dict[str, float]         # {"blinkit": 1.2, "instamart": 0.8} seconds
    total_time: float
    platforms_available: list[str]
    platforms_failed: list[str]

# ── Cart Models ──

class CartItem(BaseModel):
    matched_pair: MatchedPair
    quantity: int = 1

class DeliveryInfo(BaseModel):
    platform: str
    base_fee: float
    free_above_threshold: float
    estimated_time_minutes: int | None = None
    source: str                           # "scraped" | "default"

class PlatformCartBreakdown(BaseModel):
    platform: str
    items_total: float
    delivery_cost: float
    grand_total: float
    item_count: int

class SplitAssignment(BaseModel):
    assignments: dict[str, str]           # {item_id: platform}
    platform_breakdowns: dict[str, PlatformCartBreakdown]
    grand_total: float
    num_deliveries: int

class CartOptimizationResult(BaseModel):
    single_platform_totals: dict[str, PlatformCartBreakdown]
    optimal_split: SplitAssignment
    recommendation: str                   # "all_blinkit" | "all_instamart" | "split"
    recommendation_reason: str
    savings_vs_worst: float
    combined_rating: float | None         # Weighted avg rating across cart items
```

---

## 8. API Contracts

### 8.1 Search Endpoint

```
GET /api/search?q={query}&strategy={matching_strategy}

Query Parameters:
  q: string (required) — search term, e.g., "maggi"
  strategy: string (optional, default="hybrid") — "exact"|"token_set"|"levenshtein"|"hybrid"

Response 200:
{
  "query": "maggi",
  "matched_pairs": [
    {
      "canonical_name": "Maggi 2-Min Noodles Masala 70g",
      "confidence": 0.94,
      "confidence_label": "High",
      "products": {
        "blinkit": { "price": 14, "mrp": 15, "unit_price": 20.0, "unit_price_label": "₹20.00/100g", ... },
        "instamart": { "price": 13, "mrp": 15, "unit_price": 18.57, "unit_price_label": "₹18.57/100g", ... }
      },
      "cheaper_platform": "instamart",
      "price_diff": 1.0,
      "match_details": { "exact": 0.0, "token_set": 0.82, "levenshtein": 0.71, "hybrid": 0.94 }
    }
  ],
  "unmatched": {
    "blinkit": [...],
    "instamart": [...]
  },
  "metadata": {
    "timestamp": "2026-09-12T03:00:00+05:30",
    "cache_hit": false,
    "fetch_times": { "blinkit": 1.2, "instamart": 0.8 },
    "total_time": 1.5,
    "platforms_available": ["blinkit", "instamart"],
    "platforms_failed": []
  }
}
```

### 8.2 Cart Optimization Endpoint

```
POST /api/cart/optimize

Request Body:
{
  "items": [
    {
      "id": "cart-1",
      "canonical_name": "Maggi 2-Min Noodles 70g",
      "prices": { "blinkit": 14, "instamart": 13 },
      "in_stock": { "blinkit": true, "instamart": true },
      "quantity": 2
    },
    ...
  ]
}

Response 200:
{
  "single_platform_totals": {
    "blinkit": { "items_total": 103, "delivery_cost": 0, "grand_total": 103 },
    "instamart": { "items_total": 98, "delivery_cost": 0, "grand_total": 98 }
  },
  "optimal_split": {
    "assignments": { "cart-1": "instamart", "cart-2": "blinkit", "cart-3": "instamart" },
    "grand_total": 95,
    "num_deliveries": 2
  },
  "recommendation": "all_instamart",
  "recommendation_reason": "All items from Instamart costs ₹98 with free delivery. Smart split saves ₹3 more but requires 2 deliveries.",
  "savings_vs_worst": 5.0
}
```

### 8.3 Health Endpoint

```
GET /api/health

Response 200:
{
  "status": "healthy",
  "platforms": {
    "blinkit": { "status": "up", "last_check": "...", "avg_response_ms": 1200 },
    "instamart": { "status": "up", "last_check": "...", "avg_response_ms": 800 }
  },
  "cache_size": 12,
  "uptime_seconds": 3600
}
```

---

## 9. Product Matching Engine (Deep Dive)

### 9.1 The Pipeline

```
Raw Input: "Maggi 2-Minute Noodles Masala 70g" (Blinkit)
           "MAGGI 2-Min Masala Instant Noodles 70 g" (Instamart)

Stage 1 — Normalization:
  → lowercase, strip ™®, collapse whitespace
  → "maggi 2-minute noodles masala 70g"
  → "maggi 2-min masala instant noodles 70 g"

Stage 2 — Structured Extraction:
  → brand: "maggi" (both)
  → weight: WeightInfo(value=70, unit="g", base_value=70.0)
  → remaining: "2-minute noodles masala" / "2-min masala instant noodles"

Stage 3 — Hard Gate:
  → brand_match? YES (both "maggi")
  → weight_match? YES (70g == 70g, within ±5% tolerance)
  → PASS gate → proceed to soft matching

Stage 4 — Soft Matching (multiple strategies):
  → Token Set Ratio: {"2", "minute", "noodles", "masala"} vs {"2", "min", "masala", "instant", "noodles"}
     Intersection = {"2", "masala", "noodles"}, Union = {"2", "minute", "min", "noodles", "masala", "instant"}
     Jaccard = 3/6 = 0.50... BUT "minute"≈"min" (prefix match) → adjusted = 0.67
  → SequenceMatcher: ratio("2-minute noodles masala", "2-min masala instant noodles") = 0.72
  → Hybrid: max(token_set_adjusted, sequence_ratio) = 0.72

Stage 5 — Confidence Scoring:
  confidence = 0.0
  + 0.30 (brand match)
  + 0.30 (weight match)
  + 0.72 * 0.30 = 0.216 (name similarity, scaled)
  + 0.10 (variant match — both "masala")
  = 0.916 → "High Confidence"
```

### 9.2 Matching Strategies Available

| Strategy | Algorithm | Best For | Worst For |
|----------|-----------|----------|-----------|
| **Exact** | `normalize(a) == normalize(b)` | Identical products | Any name variation |
| **Token Set Ratio** | Jaccard on word tokens, order-independent | Reordered words | Different word count |
| **Levenshtein** | Character edit distance / ratio | Minor typos, abbreviations | Different word order |
| **Hybrid (Default)** | Hard gate (brand+weight) → soft match | Overall best accuracy | Still fails on vernacular |

### 9.3 Where It Breaks (Honest Assessment for Design Note)

| Failure Case | Example | Why It Fails | Mitigation |
|-------------|---------|-------------|------------|
| **Vernacular names** | "Dahi 400g" vs "Curd 400g" | Zero token overlap | Brand alias + vernacular dictionary |
| **Multipack ambiguity** | "Pack of 4 × 70g" vs "280g" | Weight extraction complexity | Multipack regex expansion |
| **Store-brand products** | "Blinkit Fresh Milk" vs "Instamart Milk" | Platform name in product name | Strip known platform names |
| **Promotional suffixes** | "Maggi 70g + Free Bowl" vs "Maggi 70g" | Extra tokens degrade similarity | Strip known promo phrases |
| **Flavor vs base product** | "Coca-Cola Zero 300ml" vs "Coca-Cola Diet 300ml" | High similarity, different product | Variant extraction helps but not perfect |

---

## 10. Smart Cart & Optimizer

### 10.1 Algorithm: Split-Cart with Delivery Optimization

```python
def optimize_cart(items: list[CartItem], delivery: dict[str, DeliveryInfo]) -> CartOptimizationResult:
    platforms = list(delivery.keys())  # ["blinkit", "instamart"]
    n = len(items)
    
    # Precompute single-platform totals
    single_totals = {}
    for platform in platforms:
        items_total = sum(
            item.prices.get(platform, float('inf')) * item.quantity
            for item in items
        )
        delivery_cost = compute_delivery(platform, items_total, delivery)
        single_totals[platform] = items_total + delivery_cost
    
    # Brute-force optimal split (2^N for N ≤ 20)
    if n <= 20:
        best_total = float('inf')
        best_assignment = {}
        
        for mask in range(2**n):
            subtotals = {p: 0.0 for p in platforms}
            assignment = {}
            valid = True
            
            for i, item in enumerate(items):
                p = platforms[(mask >> i) & 1]
                price = item.prices.get(p)
                if price is None or not item.in_stock.get(p, False):
                    valid = False
                    break
                subtotals[p] += price * item.quantity
                assignment[item.id] = p
            
            if not valid:
                continue
            
            total = sum(
                subtotals[p] + compute_delivery(p, subtotals[p], delivery)
                for p in platforms
                if subtotals[p] > 0
            )
            
            if total < best_total:
                best_total = total
                best_assignment = assignment.copy()
    
    # Generate recommendation
    best_single = min(single_totals, key=single_totals.get)
    if best_total < single_totals[best_single] - 5:  # > ₹5 savings to justify split
        recommendation = "split"
        reason = f"Split saves ₹{single_totals[best_single] - best_total:.0f} vs best single platform"
    else:
        recommendation = f"all_{best_single}"
        reason = f"All from {best_single} is simplest. Split saves only ₹{single_totals[best_single] - best_total:.0f} — not worth 2 deliveries."
    
    return CartOptimizationResult(...)
```

### 10.2 Complexity Analysis

| Cart Size | Brute Force Iterations | Time (est.) | Approach |
|-----------|----------------------|-------------|----------|
| 5 items | 32 | < 1ms | Brute force |
| 10 items | 1,024 | < 1ms | Brute force |
| 15 items | 32,768 | ~5ms | Brute force |
| 20 items | 1,048,576 | ~50ms | Brute force (still fine) |
| 25+ items | 33M+ | > 1s | Switch to greedy heuristic |

For a grocery cart (typically 5-15 items), brute force is trivially fast.

---

## 11. Error Handling & Resilience

### 11.1 Error Taxonomy

```python
class PlatformError(Exception):
    """Base exception for all platform-related errors."""
    platform: str

class PlatformTimeoutError(PlatformError):
    """Platform didn't respond within timeout."""

class PlatformBlockedError(PlatformError):
    """Platform detected us as a bot."""

class PlatformParseError(PlatformError):
    """Platform returned data we couldn't parse (DOM/API changed)."""

class LocationNotServedError(PlatformError):
    """Platform doesn't deliver to this location."""
```

### 11.2 Resilience Matrix

| Failure | Detection | Response | User Sees |
|---------|-----------|----------|-----------|
| One platform down | asyncio.TimeoutError after 10s | Return other platform's results | "⚠️ Blinkit unavailable. Showing Instamart results." |
| Both platforms down | Both tasks fail | Serve from cache if available | "Showing cached results from X min ago" or error |
| Rate limited | 429 status / empty response | Back off, serve cached | "Rate limited. Showing recent cached results." |
| Parse failure | KeyError / unexpected schema | Log error, skip platform | Same as "platform down" |
| No results found | Empty response | Show helpful message | "No results for 'xyz' on [platform]" |
| Matcher failure | Exception in matching | Return unmatched lists | Results shown without pairing |

### 11.3 Circuit Breaker (Per Adapter)

```python
class CircuitBreaker:
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, skip adapter
    HALF_OPEN = "half_open" # Testing if recovered
    
    failure_threshold: int = 3      # Open after 3 consecutive failures
    recovery_timeout: int = 300     # Try again after 5 minutes
```

---

## 12. Scalability Analysis

| Scale Factor | Current Design | What Changes | First Bottleneck |
|-------------|---------------|-------------|-----------------|
| **1 user, 2 platforms** | In-memory cache, async fetch | Nothing | N/A |
| **10 locations** | Hardcoded DTU | Location as parameter, cache key includes location | Cache size grows 10× |
| **100 users** | Single server | Need connection pooling for HTTP clients | Concurrent scraping limit |
| **1000 users** | Can't spawn 1000 browser instances | Worker pool + task queue (Celery/RQ) | Memory & CPU |
| **10 platforms** | 2 adapters | Add adapter per platform (OCP) | Total response time (slowest platform) → use SSE streaming |
| **10K+ users** | Need pre-computed catalog | Offline scraping → product database → API lookup | Architecture fundamentally changes to pull-model |

---

## 13. Tech Stack Decision (Merged from 3 LLMs)

### The Debate Summary

| LLM | Recommendation | Primary Argument |
|-----|---------------|-----------------|
| **LLM-1 (Claude Opus)** | Python FastAPI + Vanilla JS | Async native, best scraping/matching ecosystem |
| **LLM-2 (Architecture)** | Node.js Express + Playwright | Single language, simpler evaluator setup |
| **LLM-3 (DX/Impression)** | Python FastAPI + Vanilla JS | Readability, Pydantic contracts, evaluator signal |

### Final Verdict: **Python (FastAPI) + Vanilla HTML/CSS/JS**

**Decisive factors:**
1. **2 of 3 LLMs** independently chose Python FastAPI
2. Python's `difflib`, regex, and data manipulation advantages are critical for the matching engine (the core evaluated component)
3. Pydantic models serve as self-documenting data contracts — the evaluator sees your schema and understands your entire data flow
4. FastAPI's auto-generated `/docs` endpoint gives the evaluator an interactive API playground for free
5. Vanilla JS frontend = zero build step = the evaluator opens `localhost:8000` and everything works
6. LLM-2's concern about setup friction is addressed by: clear README, `requirements.txt` with pinned versions, and a `start.sh`/`start.bat` script

**Mitigating the Node.js dissent:**
- Include `start.bat` (Windows) and `start.sh` (Mac/Linux) that create venv, install deps, and start server in one click
- Pin all dependencies to avoid pip wheel compilation issues
- Zero C-extension dependencies (no numpy, no compiled packages)

---

## 14. Project Structure

```
dtu-grocery-compare/
│
├── main.py                          # FastAPI app entry + startup
├── requirements.txt                 # Pinned, pure-Python deps
├── start.sh                         # One-click setup + run (Unix)
├── start.bat                        # One-click setup + run (Windows)
├── README.md                        # Setup guide for evaluators
├── DESIGN_NOTE.md                   # One-page design note
├── .env.example                     # Environment variables template
│
├── app/
│   ├── __init__.py
│   ├── config.py                    # Constants, DTU coords, thresholds, feature flags
│   │
│   ├── core/                        # ── DOMAIN CORE (zero external deps) ──
│   │   ├── __init__.py
│   │   ├── ports.py                 # PlatformPort, CachePort ABCs
│   │   ├── models.py               # All Pydantic domain models
│   │   ├── normalizer.py           # Name cleaning, brand/weight extraction
│   │   ├── matcher.py              # Multi-strategy product matching
│   │   ├── strategies/             # ── Matching Strategies (Strategy Pattern) ──
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # MatchingStrategy ABC
│   │   │   ├── exact.py            # ExactMatchStrategy
│   │   │   ├── token_set.py        # TokenSetRatioStrategy
│   │   │   ├── levenshtein.py      # LevenshteinStrategy
│   │   │   └── hybrid.py           # HybridGatedStrategy (default)
│   │   └── cart_optimizer.py       # Split-cart optimization algorithm
│   │
│   ├── adapters/                    # ── INFRASTRUCTURE ADAPTERS ──
│   │   ├── __init__.py
│   │   ├── blinkit.py              # BlinkitAdapter (implements PlatformPort)
│   │   ├── instamart.py            # InstamartAdapter (implements PlatformPort)
│   │   └── fixtures/               # Offline snapshot data for evaluator fallback
│   │       ├── blinkit_maggi.json
│   │       └── instamart_maggi.json
│   │
│   ├── infrastructure/              # ── INFRASTRUCTURE SERVICES ──
│   │   ├── __init__.py
│   │   ├── cache.py                # MemoryCacheAdapter (implements CachePort)
│   │   └── platform_registry.py   # Auto-discovers and manages adapters
│   │
│   ├── api/                         # ── API LAYER ──
│   │   ├── __init__.py
│   │   ├── search.py               # GET /api/search
│   │   ├── cart.py                  # POST /api/cart/optimize
│   │   └── health.py               # GET /api/health
│   │
│   └── orchestrator.py             # Coordinates fetch → normalize → match pipeline
│
├── static/                          # ── FRONTEND ──
│   ├── index.html                   # Single-page app
│   ├── styles.css                   # Modern CSS (custom properties, grid, glassmorphism)
│   ├── app.js                       # Search controller, results renderer
│   ├── cart.js                      # Cart state management (localStorage)
│   └── optimizer.js                 # Client-side cart optimization (optional mirror)
│
├── config/                          # ── EXTERNAL CONFIG ──
│   ├── brand_aliases.json           # Known brand aliases (coke → coca-cola)
│   └── weight_patterns.json         # Regex patterns for weight extraction
│
└── tests/                           # ── TESTS ──
    ├── __init__.py
    ├── test_normalizer.py           # Unit tests for normalization
    ├── test_matcher.py              # Unit tests for matching (with real examples)
    ├── test_cart_optimizer.py        # Unit tests for cart optimization
    ├── test_strategies.py           # Tests per matching strategy
    └── fixtures/                    # Test fixture data
        ├── blinkit_sample.json
        └── instamart_sample.json
```

**Dependency flow (always inward):**
```
static/ → api/ → orchestrator → core/ (domain) ← adapters/ ← infrastructure/
                                  ↑ no outward dependencies
```

---

## 15. Rejected Alternatives

| Alternative | Why Considered | Why Rejected |
|-------------|---------------|-------------|
| **Node.js + Express** | Single language stack, simpler npm setup | Weaker matching/data manipulation ecosystem. 1 of 3 LLMs chose it; 2 chose Python. |
| **React/Next.js frontend** | Component-based UI development | Adds build step, npm version conflicts on evaluator machine. Assignment says UI polish isn't graded. |
| **Django** | Full-featured web framework | Too heavyweight. We don't need ORM, admin panel, templates. FastAPI is purpose-built for APIs. |
| **Playwright/Puppeteer (headless browser)** | Sees exactly what user sees | Heavy (launches Chromium), slow (3-5s), fragile (DOM changes), resource-intensive. LLM-3's strongest argument: "firing a full headless browser for read-only catalog search is architectural overkill." |
| **LLM-based matching** | Handles semantic similarity ("Curd" = "Dahi") | Non-deterministic, high latency (2-4s), requires API key, hides algorithmic thinking that evaluator wants to see. |
| **Redis cache** | Production-grade caching | Overkill for localhost single-user. Adds external dependency. Mentioned in scalability section as upgrade path. |
| **Scrapy** | Purpose-built scraping framework | Designed for crawling, not interactive search-and-scrape. Wrong tool for the job. |
| **MongoDB/PostgreSQL** | Persistent data storage | No persistence needed. In-memory cache + localStorage sufficient. Adds setup complexity. |

---

## Appendix: Key Configuration Constants

```python
# config.py

# Location
DTU_LOCATION = Location(lat=28.7501, lng=77.1177, label="DTU Campus", pincode="110042")

# Cache
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 100     # Max cached search results

# Scraping
REQUEST_TIMEOUT_SECONDS = 10
MAX_RESULTS_PER_PLATFORM = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Matching
CONFIDENCE_HIGH_THRESHOLD = 0.80
CONFIDENCE_MEDIUM_THRESHOLD = 0.50
WEIGHT_TOLERANCE_PCT = 5.0  # ±5% weight difference allowed for matching
DEFAULT_MATCHING_STRATEGY = "hybrid"

# Cart
DELIVERY_CONFIG = {
    "blinkit": {"base_fee": 25, "free_above": 99},
    "instamart": {"base_fee": 35, "free_above": 149},
}
SPLIT_CART_MIN_SAVINGS = 5.0  # Minimum ₹ savings to recommend split over single
MAX_CART_ITEMS_BRUTE_FORCE = 20  # Switch to greedy above this

# Server
HOST = "0.0.0.0"
PORT = 8000
```
