"""
Instamart Adapter — Fetches live product data from Swiggy Instamart desktop web.

Implements PlatformPort. Uses BrowserClient to query Swiggy Instamart live search
with DTU location cookies, capturing real /api/instamart/search/v2 API data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import urllib.parse
from typing import Optional

from app.core.models import DeliveryInfo, Location, RawListing
from app.core.ports import PlatformError, PlatformPort
from app.infrastructure.browser_client import browser_client

logger = logging.getLogger(__name__)


class InstamartAdapter(PlatformPort):
    """Adapter for Swiggy Instamart grocery platform."""

    @property
    def platform_id(self) -> str:
        return "instamart"

    @property
    def platform_name(self) -> str:
        return "Swiggy Instamart"

    @property
    def base_url(self) -> str:
        return "https://www.swiggy.com"

    async def search(
        self, query: str, location: Location
    ) -> list[RawListing]:
        """Search Instamart for products via live browser query."""
        return await self._live_search(query, location)

    async def _live_search(
        self, query: str, location: Location
    ) -> list[RawListing]:
        """Attempt live search via Swiggy Instamart's live web interface with fallback to snapshot."""
        try:
            data = await browser_client.fetch_swiggy(query)
            if data and not (isinstance(data, dict) and data.get("statusCode")):
                listings = self._parse_search_response(data)
                if listings:
                    self._save_snapshot(query, listings)
                    return listings
            elif isinstance(data, dict) and data.get("statusCode") == 429:
                logger.warning(f"Swiggy Instamart returned 429 rate limit for query '{query}'. Trying fallback snapshot.")
        except Exception as e:
            logger.warning(f"Swiggy Instamart live search error for '{query}': {e}. Trying fallback snapshot.")

        # Resilient fallback to offline snapshot if live scraping is rate limited
        snapshot = self._load_snapshot(query)
        if snapshot:
            logger.info(f"Loaded {len(snapshot)} listings from authentic Instamart snapshot for '{query}'.")
            return snapshot

        raise PlatformError(
            self.platform_id,
            f"Could not fetch live search results from Swiggy Instamart (rate limited)."
        )

    def _get_snapshot_path(self, query: str) -> Path:
        clean = re.sub(r"[^a-zA-Z0-9_]", "", query.lower().strip().replace(" ", "_"))
        return Path(__file__).parent / "snapshots" / f"{clean}.json"

    def _load_snapshot(self, query: str) -> Optional[list[RawListing]]:
        path = self._get_snapshot_path(query)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            return [RawListing(**item) for item in raw_data]
        except Exception as e:
            logger.warning(f"Failed to load snapshot for {query}: {e}")
            return None

    def _save_snapshot(self, query: str, listings: list[RawListing]) -> None:
        path = self._get_snapshot_path(query)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([item.model_dump() for item in listings], f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save snapshot for {query}: {e}")

    def _parse_search_response(self, data: dict) -> list[RawListing]:
        """Parse Swiggy Instamart API response into RawListing objects."""
        listings: list[RawListing] = []

        cards = data.get("data", {}).get("cards", []) if isinstance(data, dict) else []

        for card in cards:
            if not isinstance(card, dict):
                continue

            c = card.get("card", {}).get("card", {})
            if not isinstance(c, dict):
                continue

            # Product items live inside gridElements.infoWithStyle.items
            grid_elements = c.get("gridElements", {})
            info_with_style = grid_elements.get("infoWithStyle", {}) if isinstance(grid_elements, dict) else {}
            items = info_with_style.get("items", []) if isinstance(info_with_style, dict) else []

            for it in items:
                if not isinstance(it, dict):
                    continue

                name = it.get("displayName") or it.get("name")
                if not name:
                    continue

                pid = str(it.get("productId") or "")
                in_stock = bool(it.get("inStock", True))
                variations = it.get("variations", [])

                if variations and isinstance(variations, list):
                    for v in variations:
                        if not isinstance(v, dict):
                            continue

                        # Extract pack size / weight description
                        q_desc = v.get("quantityDescription") or ""
                        weight_g = v.get("weightInGrams")
                        raw_weight = q_desc or (f"{weight_g} g" if weight_g else None)

                        # Extract price & MRP
                        price_dict = v.get("price", {})
                        offer_price_obj = price_dict.get("offerPrice", {}) if isinstance(price_dict, dict) else {}
                        price_val = offer_price_obj.get("units") if isinstance(offer_price_obj, dict) else None
                        try:
                            price = float(price_val) if price_val is not None else 0.0
                        except (ValueError, TypeError):
                            price = 0.0

                        if price <= 0:
                            continue

                        mrp_obj = price_dict.get("mrp", {}) if isinstance(price_dict, dict) else {}
                        mrp_val = mrp_obj.get("units") if isinstance(mrp_obj, dict) else None
                        try:
                            mrp = float(mrp_val) if mrp_val is not None else None
                        except (ValueError, TypeError):
                            mrp = None

                        # Extract image
                        image_ids = v.get("imageIds", [])
                        image_url = None
                        if image_ids and isinstance(image_ids, list) and image_ids[0]:
                            image_url = f"https://instamart-media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,h_600/{image_ids[0]}"

                        spin_id = v.get("spinId") or v.get("skuId") or pid
                        query_str = f"{name} {raw_weight}" if raw_weight and raw_weight.lower() not in name.lower() else name
                        product_url = f"{self.base_url}/instamart/search?custom_back=true&query={urllib.parse.quote_plus(query_str)}"

                        # Extract rating & review count
                        r_dict = v.get("rating") or it.get("rating")
                        rating: Optional[float] = None
                        rating_count: Optional[str] = None
                        if isinstance(r_dict, dict):
                            r_val = r_dict.get("value")
                            if r_val is not None:
                                try:
                                    rating = round(float(r_val), 1)
                                except (ValueError, TypeError):
                                    rating = None
                            r_cnt = r_dict.get("count")
                            if r_cnt:
                                rating_count = str(r_cnt).strip()
                        elif isinstance(r_dict, (int, float)):
                            rating = round(float(r_dict), 1)

                        listings.append(
                            RawListing(
                                platform=self.platform_id,
                                name=name,
                                price=price,
                                mrp=mrp,
                                image_url=image_url,
                                product_url=product_url,
                                in_stock=in_stock,
                                rating=rating,
                                rating_count=rating_count,
                                raw_weight_text=raw_weight,
                                product_id=pid or (str(spin_id) if spin_id else None),
                            )
                        )
                else:
                    # Single listing without variations
                    price_val = it.get("price") or it.get("storePrice")
                    try:
                        price = float(price_val) if price_val else 0.0
                    except (ValueError, TypeError):
                        price = 0.0

                    if price <= 0:
                        continue

                    mrp_val = it.get("mrp")
                    try:
                        mrp = float(mrp_val) if mrp_val else None
                    except (ValueError, TypeError):
                        mrp = None

                    product_url = f"{self.base_url}/instamart/search?custom_back=true&query={urllib.parse.quote_plus(name)}"
                    
                    r_dict = it.get("rating")
                    rating = None
                    rating_count = None
                    if isinstance(r_dict, dict):
                        try:
                            rating = round(float(r_dict.get("value")), 1) if r_dict.get("value") is not None else None
                        except (ValueError, TypeError):
                            rating = None
                        rating_count = str(r_dict.get("count") or "").strip() or None

                    listings.append(
                        RawListing(
                            platform=self.platform_id,
                            name=name,
                            price=price,
                            mrp=mrp,
                            image_url=None,
                            product_url=product_url,
                            in_stock=in_stock,
                            rating=rating,
                            rating_count=rating_count,
                            raw_weight_text=None,
                            product_id=pid or None,
                        )
                    )

        logger.info(f"Swiggy Instamart live search parsed {len(listings)} authentic products")
        return listings

    async def get_delivery_info(self, location: Location) -> DeliveryInfo:
        return DeliveryInfo(
            platform=self.platform_id,
            base_fee=35.0,
            free_above_threshold=149.0,
            source="default",
        )

    async def health_check(self) -> bool:
        return browser_client._initialized
