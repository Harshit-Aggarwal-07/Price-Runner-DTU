"""
Blinkit Adapter — Fetches live product data from Blinkit's desktop web interface.

Implements PlatformPort. Uses BrowserClient to query Blinkit's live search page
with DTU location cookies, capturing real layout/search API data.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Optional

from app.core.models import DeliveryInfo, Location, RawListing
from app.core.ports import PlatformError, PlatformPort
from app.infrastructure.browser_client import browser_client

logger = logging.getLogger(__name__)


class BlinkitAdapter(PlatformPort):
    """Adapter for Blinkit grocery platform."""

    @property
    def platform_id(self) -> str:
        return "blinkit"

    @property
    def platform_name(self) -> str:
        return "Blinkit"

    @property
    def base_url(self) -> str:
        return "https://blinkit.com"

    async def search(
        self, query: str, location: Location
    ) -> list[RawListing]:
        """Search Blinkit for products via live browser query."""
        return await self._live_search(query, location)

    async def _live_search(
        self, query: str, location: Location
    ) -> list[RawListing]:
        """Attempt live search via Blinkit's live web interface."""
        data = await browser_client.fetch_blinkit(query)
        if not data:
            raise PlatformError(self.platform_id, "Could not fetch live search results from Blinkit.")

        return self._parse_search_response(data)

    def _parse_search_response(self, data: dict) -> list[RawListing]:
        """Parse Blinkit API layout response into RawListing objects."""
        listings: list[RawListing] = []

        # Check response snippets in layout structure
        resp = data.get("response", {})
        snippets = resp.get("snippets", []) if isinstance(resp, dict) else []

        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue

            d = snippet.get("data", {})
            if not isinstance(d, dict):
                continue

            # Extract name
            name_obj = d.get("name", {})
            name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj or "")
            if not name:
                continue

            # Extract variant / pack size text
            variant_obj = d.get("variant", {})
            raw_weight = variant_obj.get("text") if isinstance(variant_obj, dict) else str(variant_obj or "")

            # Extract selling price
            price_obj = d.get("normal_price", {})
            price_text = str(price_obj.get("text") if isinstance(price_obj, dict) else (price_obj or ""))
            price_clean = re.sub(r"[^\d.]", "", price_text)
            try:
                price = float(price_clean) if price_clean else 0.0
            except ValueError:
                price = 0.0

            if price <= 0:
                continue

            # Extract MRP
            mrp_obj = d.get("mrp", {})
            mrp_text = str(mrp_obj.get("text") if isinstance(mrp_obj, dict) else (mrp_obj or ""))
            mrp_clean = re.sub(r"[^\d.]", "", mrp_text)
            try:
                mrp = float(mrp_clean) if mrp_clean else None
            except ValueError:
                mrp = None

            # Extract image
            img_obj = d.get("image", {})
            image_url = img_obj.get("url") if isinstance(img_obj, dict) else str(img_obj or "")

            # Stock status
            in_stock = not d.get("is_sold_out", False)

            # Product ID
            product_id = str(d.get("product_id") or "")

            # Construct product deep link
            product_url = self._build_product_url(name, product_id, d)

            # Rating & Review count
            rating: Optional[float] = None
            rating_count: Optional[str] = None
            rating_obj = d.get("rating", {})
            if isinstance(rating_obj, dict):
                bar_obj = rating_obj.get("bar", {})
                if isinstance(bar_obj, dict):
                    r_val = bar_obj.get("value")
                    if r_val is not None:
                        try:
                            rating = round(float(r_val), 1)
                        except (ValueError, TypeError):
                            rating = None
                    title_obj = bar_obj.get("title", {})
                    if isinstance(title_obj, dict):
                        rating_count = str(title_obj.get("text") or "").strip() or None
                elif rating_obj.get("text"):
                    try:
                        rating = round(float(rating_obj.get("text")), 1)
                    except (ValueError, TypeError):
                        rating = None

            listings.append(
                RawListing(
                    platform=self.platform_id,
                    name=name,
                    price=price,
                    mrp=mrp,
                    image_url=image_url or None,
                    product_url=product_url,
                    in_stock=in_stock,
                    rating=rating,
                    rating_count=rating_count,
                    raw_weight_text=raw_weight or None,
                    product_id=product_id or None,
                )
            )

        logger.info(f"Blinkit live search parsed {len(listings)} authentic products")
        return listings

    def _build_product_url(self, name: str, product_id: str, data: dict) -> str:
        """Build deep-link URL for a Blinkit product."""
        # Clean slug from name
        slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug)
        if slug and product_id:
            return f"{self.base_url}/prn/{slug}/prid/{product_id}"
        elif product_id:
            return f"{self.base_url}/prn/product/prid/{product_id}"

        name_encoded = urllib.parse.quote_plus(name)
        return f"{self.base_url}/s/?q={name_encoded}"

    async def get_delivery_info(self, location: Location) -> DeliveryInfo:
        return DeliveryInfo(
            platform=self.platform_id,
            base_fee=25.0,
            free_above_threshold=99.0,
            source="default",
        )

    async def health_check(self) -> bool:
        return browser_client._initialized
