# PriceRunner DTU — The Great DTU Grocery Race
### A Build Challenge for CarDekho Group Campus Applicants

Compare grocery prices across **Blinkit** and **Swiggy Instamart** for delivery to **Delhi Technological University (DTU)** campus in one single search. Features real-time price comparison, unit-price normalization (`₹/100g`), delivery fee-aware **Smart Cart optimization**, and a responsive editorial UI with Light & Dark modes.

---

## 🚀 Quickstart (Fresh Machine Setup)

Assume you've never touched this stack before. You only need **Python 3.10+**.

### Windows (One-Click)
Double-click `start.bat` or run in terminal:
```cmd
start.bat
```

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### Manual Setup
```bash
# 1. Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
python main.py
```

Open your browser at:
- **Web App**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🏗️ Architecture: Hexagonal (Ports & Adapters)

The project strictly follows **Hexagonal Architecture** and Domain-Driven Design (DDD):

```
┌─────────────────────────────────────────────────────────────┐
│                       Delivery Layer                        │
│         FastAPI Controllers (app/api/search.py, cart.py)    │
│              Vanilla HTML/CSS/JS Frontend (static/)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Orchestration Layer                      │
│      app/orchestrator.py (Parallel Async Scraper & Matcher) │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                        Domain Core                          │
│          Zero external dependencies / pure Python           │
│   • Normalizer (app/core/normalizer.py)                     │
│   • Matcher & Strategy Pipeline (app/core/matcher.py)       │
│   • Smart Cart Optimizer (app/core/cart_optimizer.py)       │
│   • Ports / Interfaces (app/core/ports.py)                  │
└──────────────────────────────▲──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                      Adapters Layer                         │
│   • BlinkitAdapter (app/adapters/blinkit.py)                │
│   • InstamartAdapter (app/adapters/instamart.py)            │
│   • In-Memory TTLCache (app/infrastructure/cache.py)        │
│   • Offline Fixtures (app/adapters/fixtures/)               │
└─────────────────────────────────────────────────────────────┘
```

- **Pluggability (OCP)**: Adding Zepto or BigBasket requires adding a single adapter file implementing `PlatformPort`. The core matching engine and APIs remain completely untouched.
- **Fault Tolerance**: `asyncio.gather(return_exceptions=True)` ensures that if one platform fails or is rate-limited, results from the other platform still render gracefully.
- **Offline Reliability**: Includes local JSON fixtures for core campus queries (`maggi`, `milk`, `bread`, `butter`, etc.) so the app functions offline or during evaluation network restrictions.

---

## ⚡ Key Features

1. **4-Stage Hybrid Product Matcher (`app/core/strategies/hybrid.py`)**:
   - **Hard Brand Gate**: Alias normalization (`nestle maggi` $\rightarrow$ `maggi`) prevents cross-brand false positives.
   - **Hard Weight Normalization Gate**: Normalizes units and multipacks (`4x70g` $\rightarrow$ `280g`, `1 L` $\rightarrow$ `1000 ml`), enforcing a $\pm 5\%$ weight tolerance to prevent matching single packs with multipacks.
   - **Fuzzy Token & String Similarity**: Combines Jaccard token overlap with Levenshtein character similarity.
   - **Unit Price Normalization**: Computes standardized `₹/100g` or `₹/100ml` values to reveal real price efficiency.

2. **Smart Cart Split-Order Optimizer (`app/core/cart_optimizer.py`)**:
   - Buying the cheapest individual item on each app does **not** guarantee the cheapest order once delivery charges and small cart fees are factored in.
   - The optimizer runs a combinatorial $2^N$ evaluation comparing:
     - All items from Blinkit (including delivery costs).
     - All items from Instamart.
     - A **Smart Split** across both stores.
   - Generates an actionable recommendation (e.g., *"Smart Split saves ₹45 vs ordering entirely from Instamart. Requires 2 deliveries."*).

3. **Modern Editorial UI**:
   - Tactile Light Mode inspired by modern canvas design (Space Grotesk typography, subtle blueprint grid, store badges).
   - Instant Dark Mode toggle with `localStorage` persistence.
   - Live search with debounce, quick-query chips, interactive store filters, and sorting (Price, Savings, Value, Ratings).
   - "Take to Home" brand link and bottom-docked collapsible disclaimer footer.

---

## 🧪 Running Automated Tests

End-to-end and UI tests are written with **Playwright** and **pytest**:

```bash
# Ensure server is running on http://localhost:8000, then:
pytest test_e2e.py test_theme_and_ui.py -v
```

Tests verify:
- Homepage loading and accessibility elements
- Live product query matching and comparison card rendering
- Add to cart and Smart Cart combinatorial optimization calculation
- Light / Dark theme toggling and `localStorage` persistence
- "Take to Home" header logo reset behavior
- Bottom-docked collapsible footer toggle

---

## 📁 Repository Structure

```
├── app/
│   ├── adapters/               # Platform scrapers (Blinkit, Instamart) & fixtures
│   ├── api/                    # FastAPI routes (search, cart, health)
│   ├── core/                   # Pure domain business logic & ports
│   │   ├── strategies/         # Matching strategies (Hybrid, Token Set, Levenshtein, Exact)
│   │   ├── cart_optimizer.py   # 2^N combinatorial cart optimizer
│   │   ├── matcher.py          # Matcher engine
│   │   ├── normalizer.py       # Weight, brand, and pack normalizer
│   │   └── models.py           # Domain Pydantic models
│   ├── infrastructure/         # Cache & platform registry
│   └── orchestrator.py         # Async scraper orchestrator
├── static/                     # Frontend assets (Vanilla HTML/CSS/JS)
│   ├── app.js                  # Search controller & UI state
│   ├── cart.js                 # Cart manager & optimizer client
│   ├── styles.css              # Custom design system (Light & Dark)
│   └── index.html              # Main application shell
├── design_note.md              # 1-page architecture & technical decision note (PDF req #2)
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── start.bat                   # Windows one-click start script
├── start.sh                    # Linux/macOS start script
├── test_e2e.py                 # Playwright E2E tests
└── test_theme_and_ui.py        # Theme, navigation, and UI tests
```

---

## 📄 Deliverables Summary

1. **Codebase & Setup**: Documented in this `README.md`.
2. **One-Page Design Note**: Available in [`design_note.md`](design_note.md).
3. **Screen Recording**: Unlisted walkthrough link submitted in the Google Form.
