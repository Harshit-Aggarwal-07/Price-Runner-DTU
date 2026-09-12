"""
Cart API — POST /api/cart/optimize endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.cart_optimizer import optimize_cart
from app.core.models import CartOptimizeRequest, CartOptimizationResult

router = APIRouter(prefix="/api", tags=["Cart"])


@router.post("/cart/optimize", response_model=CartOptimizationResult)
async def optimize_cart_endpoint(request: CartOptimizeRequest):
    """
    Optimize a cart of items across platforms.

    Finds the cheapest combination considering:
    - Per-item prices on each platform
    - Delivery costs and free-delivery thresholds
    - Stock availability

    Returns a recommendation: order from one platform, or split across platforms.
    """
    return optimize_cart(request.items)
