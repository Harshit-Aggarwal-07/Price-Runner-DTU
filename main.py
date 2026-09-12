"""
DTU Grocery Price Compare — Main Application Entry Point

Starts the FastAPI server with:
- Static file serving (frontend)
- API routes (search, cart, health)
- Platform adapter initialization
- Auto-generated API docs at /docs
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT, DTU_LOCATION
from app.core.models import Location
from app.infrastructure.browser_client import browser_client
from app.infrastructure.cache import MemoryCacheAdapter
from app.infrastructure.platform_registry import PlatformRegistry
from app.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Globals (set during startup) ──
registry = PlatformRegistry()
cache = MemoryCacheAdapter()
orchestrator: Orchestrator | None = None

location = Location(
    latitude=DTU_LOCATION.latitude,
    longitude=DTU_LOCATION.longitude,
    label=DTU_LOCATION.label,
    pincode=DTU_LOCATION.pincode,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    global orchestrator

    logger.info("=" * 60)
    logger.info("  DTU Grocery Price Compare — Starting Up")
    logger.info("=" * 60)
    logger.info(f"  Location: {location.label} ({location.pincode})")

    # Initialize live browser client for authentic scraping
    await browser_client.initialize()

    # Initialize platform adapters
    await registry.initialize()
    adapters = registry.get_all_adapters()
    logger.info(f"  Loaded {len(adapters)} platform adapter(s): {registry.get_platform_ids()}")

    # Create orchestrator with injected dependencies
    orchestrator = Orchestrator(adapters=adapters, cache=cache)

    # Inject into API modules
    from app.api.search import init_search_api
    from app.api.health import init_health_api

    init_search_api(orchestrator, location)
    init_health_api(registry, cache)

    logger.info("  Server ready!")
    logger.info(f"  Open http://localhost:{PORT} in your browser")
    logger.info(f"  API docs at http://localhost:{PORT}/docs")
    logger.info("=" * 60)

    yield  # Server is running

    logger.info("Shutting down...")
    await browser_client.close()


# ── Create App ──

app = FastAPI(
    title="DTU Grocery Price Compare",
    description=(
        "Compare grocery prices across Blinkit and Instamart for DTU Campus delivery. "
        "Features smart cart optimization, multi-strategy product matching, and unit price comparison."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (allow frontend on same origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API Routes ──

from app.api.search import router as search_router
from app.api.cart import router as cart_router
from app.api.health import router as health_router

app.include_router(search_router)
app.include_router(cart_router)
app.include_router(health_router)

# ── Serve Frontend ──

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse(STATIC_DIR / "index.html")


# Mount static files (CSS, JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Run ──

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        loop="asyncio",
        log_level="info",
    )
