"""
Product Matcher — Cross-platform product matching engine.

Takes normalized products from two platforms and produces:
- Matched pairs (same product on both platforms, with confidence)
- Unmatched products (available on only one platform)

Supports multiple matching strategies for comparison (debug view).
"""

from __future__ import annotations

from app.config import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    DEFAULT_MATCHING_STRATEGY,
    WEIGHT_TOLERANCE_PCT,
)
from app.core.models import (
    ConfidenceLevel,
    MatchedPair,
    MatchResult,
    NormalizedProduct,
    SearchMetadata,
    Location,
)
from app.core.ports import MatchingStrategy
from app.core.strategies.exact import ExactMatchStrategy
from app.core.strategies.hybrid import HybridGatedStrategy
from app.core.strategies.levenshtein import LevenshteinStrategy
from app.core.strategies.token_set import TokenSetRatioStrategy


# ── Registry of all available strategies ──

_STRATEGIES: dict[str, MatchingStrategy] = {
    "exact": ExactMatchStrategy(),
    "token_set": TokenSetRatioStrategy(),
    "levenshtein": LevenshteinStrategy(),
    "hybrid": HybridGatedStrategy(),
}


def get_available_strategies() -> list[str]:
    """Return list of available strategy IDs."""
    return list(_STRATEGIES.keys())


def match_products(
    platform_a_products: list[NormalizedProduct],
    platform_b_products: list[NormalizedProduct],
    strategy: str = DEFAULT_MATCHING_STRATEGY,
    include_all_strategies: bool = False,
    query: str = "",
    location: Location | None = None,
    metadata: SearchMetadata | None = None,
) -> MatchResult:
    """
    Match products across two platforms.

    Args:
        platform_a_products: Products from first platform
        platform_b_products: Products from second platform
        strategy: Which strategy to use for primary matching
        include_all_strategies: If True, compute scores for ALL strategies (debug view)
        query: Original search query
        location: Search location
        metadata: Search metadata to include in result

    Returns:
        MatchResult with matched pairs and unmatched products
    """
    if strategy not in _STRATEGIES:
        strategy = DEFAULT_MATCHING_STRATEGY

    primary_strategy = _STRATEGIES[strategy]

    matched_pairs: list[MatchedPair] = []
    used_b_indices: set[int] = set()

    # For each product in platform A, find the best match in platform B
    for product_a in platform_a_products:
        best_match_idx: int | None = None
        best_score: float = 0.0
        best_all_scores: dict[str, float] = {}

        for j, product_b in enumerate(platform_b_products):
            if j in used_b_indices:
                continue

            # Hard Gate: Incompatible weights, units, or pack counts can NEVER match
            if product_a.weight is not None and product_b.weight is not None:
                if not product_a.weight.is_compatible(product_b.weight, WEIGHT_TOLERANCE_PCT):
                    continue
            elif (product_a.weight is None) != (product_b.weight is None):
                # One product has weight and the other does not -> cannot guarantee unit parity
                continue

            # Compute primary strategy score
            score = primary_strategy.compute_similarity(product_a, product_b)

            # Optionally compute all strategy scores
            all_scores: dict[str, float] = {}
            if include_all_strategies:
                for sid, strat in _STRATEGIES.items():
                    all_scores[sid] = round(
                        strat.compute_similarity(product_a, product_b), 4
                    )

            if score > best_score:
                best_score = score
                best_match_idx = j
                best_all_scores = all_scores

        # Accept match if above medium threshold
        if best_match_idx is not None and best_score >= CONFIDENCE_MEDIUM_THRESHOLD:
            product_b = platform_b_products[best_match_idx]
            used_b_indices.add(best_match_idx)

            pair = _create_matched_pair(
                product_a, product_b, best_score, best_all_scores
            )
            matched_pairs.append(pair)

    # Collect unmatched products
    unmatched_a = [
        p for i, p in enumerate(platform_a_products)
        if not any(
            p.product_id == mp.products.get(p.platform, NormalizedProduct(
                platform="", raw_name="", normalized_name="", price=0
            )).product_id
            for mp in matched_pairs
        )
    ]
    # Simpler: track which A products were matched
    matched_a_names = {
        mp.products.get(platform_a_products[0].platform if platform_a_products else "", NormalizedProduct(
            platform="", raw_name="", normalized_name="", price=0
        )).raw_name
        for mp in matched_pairs
    }

    # Re-derive unmatched properly
    platform_a_id = platform_a_products[0].platform if platform_a_products else "unknown_a"
    platform_b_id = platform_b_products[0].platform if platform_b_products else "unknown_b"

    matched_a_raw = set()
    matched_b_raw = set()
    for mp in matched_pairs:
        for pid, prod in mp.products.items():
            if pid == platform_a_id:
                matched_a_raw.add(prod.raw_name)
            else:
                matched_b_raw.add(prod.raw_name)

    unmatched = {
        platform_a_id: [p for p in platform_a_products if p.raw_name not in matched_a_raw],
        platform_b_id: [p for p in platform_b_products if p.raw_name not in matched_b_raw],
    }

    # Sort matched pairs by confidence (highest first)
    matched_pairs.sort(key=lambda mp: mp.confidence, reverse=True)

    return MatchResult(
        query=query,
        location=location or Location(latitude=0, longitude=0),
        matched_pairs=matched_pairs,
        unmatched=unmatched,
        metadata=metadata or SearchMetadata(),
    )


def _create_matched_pair(
    a: NormalizedProduct,
    b: NormalizedProduct,
    confidence: float,
    all_strategy_scores: dict[str, float],
) -> MatchedPair:
    """Create a MatchedPair from two products and their similarity score."""

    # Determine canonical name (prefer the longer, more descriptive name)
    canonical = a.raw_name if len(a.raw_name) >= len(b.raw_name) else b.raw_name

    # Determine cheaper platform
    cheaper: str | None = None
    price_diff = abs(a.price - b.price)
    price_diff_pct = 0.0

    if a.price < b.price:
        cheaper = a.platform
        price_diff_pct = round((price_diff / b.price) * 100, 1)
    elif b.price < a.price:
        cheaper = b.platform
        price_diff_pct = round((price_diff / a.price) * 100, 1)

    # Unit price comparison
    unit_price_winner: str | None = None
    unit_price_diff: float | None = None
    if a.unit_price is not None and b.unit_price is not None:
        if a.unit_price < b.unit_price:
            unit_price_winner = a.platform
            unit_price_diff = round(b.unit_price - a.unit_price, 2)
        elif b.unit_price < a.unit_price:
            unit_price_winner = b.platform
            unit_price_diff = round(a.unit_price - b.unit_price, 2)

    # Confidence label
    if confidence >= CONFIDENCE_HIGH_THRESHOLD:
        label = ConfidenceLevel.HIGH
    elif confidence >= CONFIDENCE_MEDIUM_THRESHOLD:
        label = ConfidenceLevel.MEDIUM
    else:
        label = ConfidenceLevel.LOW

    return MatchedPair(
        canonical_name=canonical,
        confidence=round(confidence, 4),
        confidence_label=label,
        products={a.platform: a, b.platform: b},
        cheaper_platform=cheaper,
        price_diff=round(price_diff, 2),
        price_diff_pct=price_diff_pct,
        unit_price_winner=unit_price_winner,
        unit_price_diff=unit_price_diff,
        match_details=all_strategy_scores,
    )
