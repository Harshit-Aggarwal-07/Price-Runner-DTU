"""
Cart Optimizer — Split-cart optimization with delivery costs.

Finds the cheapest way to order cart items across platforms,
factoring in per-platform delivery costs and free-delivery thresholds.

Key insight: cheapest per-item ≠ cheapest total.
Splitting saves on items but costs extra delivery fees.
"""

from __future__ import annotations

from app.config import (
    DELIVERY_CONFIG,
    MAX_CART_ITEMS_BRUTE_FORCE,
    SPLIT_CART_MIN_SAVINGS,
)
from app.core.models import (
    CartItemRequest,
    CartOptimizationResult,
    PlatformCartBreakdown,
    SplitAssignment,
)


def compute_delivery_cost(platform: str, subtotal: float) -> float:
    """Compute delivery cost for a platform given the cart subtotal."""
    config = DELIVERY_CONFIG.get(platform, {"base_fee": 30.0, "free_above": 149.0})
    if subtotal <= 0:
        return 0.0
    if subtotal >= config["free_above"]:
        return 0.0
    return config["base_fee"]


def optimize_cart(items: list[CartItemRequest]) -> CartOptimizationResult:
    """
    Find the optimal assignment of cart items to platforms.

    For ≤ MAX_CART_ITEMS_BRUTE_FORCE items, uses brute-force (2^N).
    For larger carts, uses a greedy heuristic.

    Returns comparison of: all-from-each-platform vs optimal-split,
    with a human-readable recommendation.
    """
    platforms = list(DELIVERY_CONFIG.keys())

    if not items:
        return CartOptimizationResult(
            single_platform_totals={},
            recommendation="none",
            recommendation_reason="Cart is empty.",
        )

    # ── Compute single-platform totals ──
    single_totals: dict[str, PlatformCartBreakdown] = {}

    for platform in platforms:
        items_total = 0.0
        item_count = 0
        has_oos = False

        for item in items:
            price = item.prices.get(platform)
            in_stock = item.in_stock.get(platform, True)

            if price is not None and in_stock:
                items_total += price * item.quantity
                item_count += 1
            elif not in_stock:
                has_oos = True

        delivery = compute_delivery_cost(platform, items_total)
        label = DELIVERY_CONFIG.get(platform, {}).get("platform_label", platform.title())

        single_totals[platform] = PlatformCartBreakdown(
            platform=platform,
            platform_label=label,
            items_total=round(items_total, 2),
            delivery_cost=round(delivery, 2),
            grand_total=round(items_total + delivery, 2),
            item_count=item_count,
            has_oos_items=has_oos,
        )

    # ── Optimal split (brute force or greedy) ──
    n = len(items)
    optimal_split = None

    if n <= MAX_CART_ITEMS_BRUTE_FORCE:
        optimal_split = _brute_force_split(items, platforms)
    else:
        optimal_split = _greedy_split(items, platforms)

    # ── Generate recommendation ──
    # Find best single-platform option (excluding those with OOS)
    valid_singles = {
        pid: bd for pid, bd in single_totals.items()
        if not bd.has_oos_items and bd.item_count == len(items)
    }

    if not valid_singles:
        # Some items unavailable on single platforms — recommend split or best available
        if optimal_split:
            recommendation = "split"
            reason = (
                "Not all items are available on a single platform. "
                f"Smart split across {optimal_split.num_deliveries} platforms "
                f"covers all items for ₹{optimal_split.grand_total:.0f}."
            )
        else:
            # Fall back to the platform with most items
            best_p = max(single_totals.values(), key=lambda x: x.item_count)
            recommendation = f"all_{best_p.platform}"
            reason = (
                f"{best_p.platform_label} has the most items available "
                f"({best_p.item_count}/{len(items)})."
            )
    else:
        best_single_id = min(valid_singles, key=lambda pid: valid_singles[pid].grand_total)
        best_single = valid_singles[best_single_id]

        if optimal_split and optimal_split.grand_total < best_single.grand_total - SPLIT_CART_MIN_SAVINGS:
            savings = best_single.grand_total - optimal_split.grand_total
            recommendation = "split"
            reason = (
                f"Smart split saves ₹{savings:.0f} vs ordering everything from "
                f"{best_single.platform_label} (₹{optimal_split.grand_total:.0f} vs "
                f"₹{best_single.grand_total:.0f}). Requires {optimal_split.num_deliveries} deliveries."
            )
        else:
            recommendation = f"all_{best_single_id}"
            if optimal_split:
                split_savings = best_single.grand_total - optimal_split.grand_total
                if split_savings > 0:
                    reason = (
                        f"Order everything from {best_single.platform_label} "
                        f"(₹{best_single.grand_total:.0f}). Split saves only "
                        f"₹{split_savings:.0f} — not worth {optimal_split.num_deliveries} deliveries."
                    )
                else:
                    reason = (
                        f"Order everything from {best_single.platform_label} "
                        f"(₹{best_single.grand_total:.0f}) — cheapest option with single delivery."
                    )
            else:
                reason = (
                    f"Order everything from {best_single.platform_label} "
                    f"(₹{best_single.grand_total:.0f})."
                )

    # Savings vs worst option
    all_totals = [bd.grand_total for bd in single_totals.values() if bd.item_count > 0]
    if optimal_split:
        all_totals.append(optimal_split.grand_total)
    worst = max(all_totals) if all_totals else 0
    best = min(all_totals) if all_totals else 0
    savings_vs_worst = round(worst - best, 2)

    return CartOptimizationResult(
        single_platform_totals=single_totals,
        optimal_split=optimal_split,
        recommendation=recommendation,
        recommendation_reason=reason,
        savings_vs_worst=savings_vs_worst,
    )


def _brute_force_split(
    items: list[CartItemRequest],
    platforms: list[str],
) -> SplitAssignment | None:
    """Brute-force optimal split for small carts (2^N iterations)."""
    n = len(items)
    best_total = float("inf")
    best_assignment: dict[str, str] | None = None
    best_subtotals: dict[str, float] | None = None

    for mask in range(2**n):
        subtotals: dict[str, float] = {p: 0.0 for p in platforms}
        assignment: dict[str, str] = {}
        valid = True

        for i, item in enumerate(items):
            p = platforms[(mask >> i) & 1]
            price = item.prices.get(p)
            in_stock = item.in_stock.get(p, True)

            if price is None or not in_stock:
                valid = False
                break

            subtotals[p] += price * item.quantity
            assignment[item.id] = p

        if not valid:
            continue

        total = sum(
            subtotals[p] + compute_delivery_cost(p, subtotals[p])
            for p in platforms
            if subtotals[p] > 0
        )

        if total < best_total:
            best_total = total
            best_assignment = assignment.copy()
            best_subtotals = subtotals.copy()

    if best_assignment is None or best_subtotals is None:
        return None

    # Build platform breakdowns
    breakdowns: dict[str, PlatformCartBreakdown] = {}
    num_deliveries = 0
    for p in platforms:
        if best_subtotals[p] > 0:
            delivery = compute_delivery_cost(p, best_subtotals[p])
            num_deliveries += 1
            label = DELIVERY_CONFIG.get(p, {}).get("platform_label", p.title())
            items_on_platform = sum(1 for v in best_assignment.values() if v == p)
            breakdowns[p] = PlatformCartBreakdown(
                platform=p,
                platform_label=label,
                items_total=round(best_subtotals[p], 2),
                delivery_cost=round(delivery, 2),
                grand_total=round(best_subtotals[p] + delivery, 2),
                item_count=items_on_platform,
            )

    return SplitAssignment(
        assignments=best_assignment,
        platform_breakdowns=breakdowns,
        grand_total=round(best_total, 2),
        num_deliveries=num_deliveries,
    )


def _greedy_split(
    items: list[CartItemRequest],
    platforms: list[str],
) -> SplitAssignment | None:
    """Greedy heuristic for large carts: assign each item to cheapest platform."""
    subtotals: dict[str, float] = {p: 0.0 for p in platforms}
    assignment: dict[str, str] = {}

    for item in items:
        best_p = None
        best_price = float("inf")

        for p in platforms:
            price = item.prices.get(p)
            in_stock = item.in_stock.get(p, True)
            if price is not None and in_stock and price < best_price:
                best_price = price
                best_p = p

        if best_p is None:
            continue  # Item not available anywhere

        assignment[item.id] = best_p
        subtotals[best_p] += best_price * item.quantity

    # Consolidation check: if splitting costs more in delivery than it saves,
    # move everything to the platform with the higher subtotal
    active_platforms = [p for p in platforms if subtotals[p] > 0]
    if len(active_platforms) == 2:
        split_total = sum(
            subtotals[p] + compute_delivery_cost(p, subtotals[p])
            for p in active_platforms
        )
        for consolidate_to in active_platforms:
            consol_total_items = sum(subtotals.values())
            consol_delivery = compute_delivery_cost(consolidate_to, consol_total_items)
            if consol_total_items + consol_delivery < split_total:
                # Cheaper to consolidate
                for item_id in assignment:
                    assignment[item_id] = consolidate_to
                subtotals = {p: 0.0 for p in platforms}
                subtotals[consolidate_to] = consol_total_items
                break

    # Build result
    breakdowns: dict[str, PlatformCartBreakdown] = {}
    num_deliveries = 0
    grand_total = 0.0
    for p in platforms:
        if subtotals[p] > 0:
            delivery = compute_delivery_cost(p, subtotals[p])
            num_deliveries += 1
            label = DELIVERY_CONFIG.get(p, {}).get("platform_label", p.title())
            items_on = sum(1 for v in assignment.values() if v == p)
            breakdowns[p] = PlatformCartBreakdown(
                platform=p,
                platform_label=label,
                items_total=round(subtotals[p], 2),
                delivery_cost=round(delivery, 2),
                grand_total=round(subtotals[p] + delivery, 2),
                item_count=items_on,
            )
            grand_total += subtotals[p] + delivery

    return SplitAssignment(
        assignments=assignment,
        platform_breakdowns=breakdowns,
        grand_total=round(grand_total, 2),
        num_deliveries=num_deliveries,
    )
