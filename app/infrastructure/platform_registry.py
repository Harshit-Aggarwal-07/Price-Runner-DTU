"""
Platform Registry — Auto-discovers and manages platform adapters.

Adding a new platform requires:
1. Create adapter in app/adapters/ implementing PlatformPort
2. Add platform_id to config.ENABLED_PLATFORMS
That's it. Zero other code changes (OCP).
"""

from __future__ import annotations

import importlib
import logging
from typing import Optional

from app.config import ENABLED_PLATFORMS
from app.core.ports import PlatformPort

logger = logging.getLogger(__name__)

# Maps platform_id → adapter module path
_ADAPTER_REGISTRY: dict[str, str] = {
    "blinkit": "app.adapters.blinkit",
    "instamart": "app.adapters.instamart",
    # Add new platforms here:
    # "zepto": "app.adapters.zepto",
}

# Maps platform_id → adapter class name
_ADAPTER_CLASSES: dict[str, str] = {
    "blinkit": "BlinkitAdapter",
    "instamart": "InstamartAdapter",
    # "zepto": "ZeptoAdapter",
}


class PlatformRegistry:
    """Discovers, instantiates, and manages platform adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, PlatformPort] = {}

    async def initialize(self) -> None:
        """Load and instantiate all enabled adapters."""
        for platform_id in ENABLED_PLATFORMS:
            if platform_id not in _ADAPTER_REGISTRY:
                logger.warning(
                    f"Platform '{platform_id}' enabled but no adapter registered. Skipping."
                )
                continue

            try:
                module = importlib.import_module(_ADAPTER_REGISTRY[platform_id])
                cls = getattr(module, _ADAPTER_CLASSES[platform_id])
                adapter: PlatformPort = cls()
                self._adapters[platform_id] = adapter
                logger.info(f"Loaded adapter: {adapter.platform_name} ({platform_id})")
            except Exception as e:
                logger.error(f"Failed to load adapter '{platform_id}': {e}")

    def get_adapter(self, platform_id: str) -> Optional[PlatformPort]:
        """Get a specific adapter by ID."""
        return self._adapters.get(platform_id)

    def get_all_adapters(self) -> list[PlatformPort]:
        """Get all loaded adapters."""
        return list(self._adapters.values())

    def get_platform_ids(self) -> list[str]:
        """Get IDs of all loaded platforms."""
        return list(self._adapters.keys())

    def is_loaded(self, platform_id: str) -> bool:
        """Check if a platform adapter is loaded."""
        return platform_id in self._adapters
