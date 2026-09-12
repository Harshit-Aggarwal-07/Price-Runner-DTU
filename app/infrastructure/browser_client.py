"""
Browser Client — Manages a persistent, headless Playwright Chromium instance
for live querying Blinkit and Swiggy Instamart with DTU location targeting.

Bypasses Cloudflare/Akamai bot protection by navigating with authentic browser headers,
anti-automation flags, and DTU cookies, intercepting live layout/search API JSON payloads.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.config import DTU_LOCATION

logger = logging.getLogger(__name__)


class BrowserClient:
    """Singleton-style browser service managing a shared headless Chromium session."""

    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the browser and context with DTU cookies."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing headless Chromium browser client for live scraping...")
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="Asia/Kolkata",
            )
            # Remove navigator.webdriver flag
            await self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            # Pre-load DTU cookies for both platforms
            lat_str = str(DTU_LOCATION.latitude)
            lon_str = str(DTU_LOCATION.longitude)
            await self._context.add_cookies([
                {"name": "gr_1_lat", "value": lat_str, "domain": ".blinkit.com", "path": "/"},
                {"name": "gr_1_lon", "value": lon_str, "domain": ".blinkit.com", "path": "/"},
                {"name": "city", "value": "Delhi", "domain": ".blinkit.com", "path": "/"},
                {"name": "gr_1_locality", "value": "DTU", "domain": ".blinkit.com", "path": "/"},
                {"name": "lat", "value": lat_str, "domain": ".swiggy.com", "path": "/"},
                {"name": "lng", "value": lon_str, "domain": ".swiggy.com", "path": "/"},
                {
                    "name": "address",
                    "value": f"{DTU_LOCATION.label}, Shahbad Daulatpur, Delhi {DTU_LOCATION.pincode}",
                    "domain": ".swiggy.com",
                    "path": "/",
                },
            ])

            self._initialized = True
            logger.info("Browser client ready with DTU location cookies.")

    async def fetch_blinkit(self, query: str, timeout_seconds: float = 12.0) -> Optional[dict]:
        """
        Query Blinkit live search page and intercept /v1/layout/search API response.
        """
        if not self._initialized or not self._context:
            await self.initialize()

        captured_json: Optional[dict] = None
        event = asyncio.Event()

        page = await self._context.new_page()

        async def on_response(response):
            nonlocal captured_json
            if "v1/layout/search" in response.url and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct or "text/plain" in ct:
                        captured_json = await response.json()
                        event.set()
                except Exception as e:
                    logger.debug(f"Blinkit response parse debug: {e}")

        page.on("response", on_response)

        encoded_q = urllib.parse.quote_plus(query.strip())
        target_url = f"https://blinkit.com/s/?q={encoded_q}"

        try:
            # Navigate to search page
            await page.goto(target_url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            # Wait until response is captured or timeout
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Blinkit layout/search interception timed out for query '{query}'")
            return captured_json
        except Exception as e:
            logger.error(f"Blinkit browser query error for '{query}': {e}")
            return None
        finally:
            await page.close()

    async def fetch_swiggy(self, query: str, timeout_seconds: float = 12.0) -> Optional[dict]:
        """
        Query Swiggy Instamart live search page and intercept /api/instamart/search/v2 API response.
        """
        if not self._initialized or not self._context:
            await self.initialize()

        captured_json: Optional[dict] = None
        event = asyncio.Event()

        page = await self._context.new_page()

        async def on_response(response):
            nonlocal captured_json
            if "api/instamart/search/v2" in response.url and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct:
                        captured_json = await response.json()
                        event.set()
                except Exception as e:
                    logger.debug(f"Swiggy response parse debug: {e}")

        page.on("response", on_response)

        encoded_q = urllib.parse.quote_plus(query.strip())
        target_url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={encoded_q}"

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Swiggy instamart/search interception timed out for query '{query}'")
            return captured_json
        except Exception as e:
            logger.error(f"Swiggy browser query error for '{query}': {e}")
            return None
        finally:
            await page.close()

    async def close(self) -> None:
        """Close browser resources cleanly."""
        async with self._lock:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._pw:
                await self._pw.stop()
                self._pw = None
            self._initialized = False
            logger.info("Browser client stopped.")


# Shared singleton instance
browser_client = BrowserClient()
