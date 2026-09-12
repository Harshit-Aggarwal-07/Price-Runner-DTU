"""
Hybrid Gated Strategy — The default, most accurate matching strategy.

Pipeline:
1. Hard Gate: Brand must match (if both have brands)
2. Hard Gate: Weight must be within ±5% tolerance
3. Soft Score: Combines token set overlap + sequence matcher ratio
4. Confidence: Weighted sum of brand/weight/name similarity

This strategy is deterministic and explainable — perfect for the design note.
"""

from difflib import SequenceMatcher

from app.config import WEIGHT_TOLERANCE_PCT
from app.core.models import NormalizedProduct
from app.core.ports import MatchingStrategy


class HybridGatedStrategy(MatchingStrategy):

    @property
    def strategy_name(self) -> str:
        return "Hybrid Gated"

    @property
    def strategy_id(self) -> str:
        return "hybrid"

    def compute_similarity(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> float:
        """
        Multi-stage confidence scoring:
          +0.30 for brand match
          +0.30 for weight match
          +0.30 for name similarity (token + sequence)
          +0.10 for variant match
        """
        confidence = 0.0

        # ── Stage 1: Brand Gate ──
        brand_match = self._check_brand(a, b)
        if brand_match is True:
            confidence += 0.30
        elif brand_match is False:
            # Both have brands, they differ → strong negative signal
            # Still continue but cap confidence
            return max(0.0, self._soft_name_score(a, b) * 0.3)

        # ── Stage 2: Weight Gate ──
        weight_match = self._check_weight(a, b)
        if weight_match is True:
            confidence += 0.30
        elif weight_match is False:
            # Weights exist and differ → these are different products
            return confidence  # Only brand score at most

        # ── Stage 3: Name Similarity ──
        name_score = self._soft_name_score(a, b)
        confidence += name_score * 0.30

        # ── Stage 4: Variant Match ──
        if a.variant and b.variant:
            if a.variant == b.variant:
                confidence += 0.10
            else:
                # Different variants of same brand+weight → penalize slightly
                confidence -= 0.05

        return min(1.0, max(0.0, confidence))

    def _check_brand(self, a: NormalizedProduct, b: NormalizedProduct) -> bool | None:
        """
        Returns:
          True  — both have brands and they match
          False — both have brands and they differ
          None  — one or both have no brand (inconclusive)
        """
        if a.brand and b.brand:
            return a.brand == b.brand
        return None

    def _check_weight(self, a: NormalizedProduct, b: NormalizedProduct) -> bool | None:
        """
        Returns:
          True  — weights within tolerance
          False — weights exist but differ beyond tolerance
          None  — one or both have no weight info
        """
        if a.weight and b.weight:
            return a.weight.is_compatible(b.weight, WEIGHT_TOLERANCE_PCT)
        return None

    def _soft_name_score(self, a: NormalizedProduct, b: NormalizedProduct) -> float:
        """Combined token set + sequence matcher score."""
        tokens_a = set(a.name_tokens)
        tokens_b = set(b.name_tokens)

        # Token set overlap (Jaccard)
        jaccard = 0.0
        if tokens_a or tokens_b:
            union = tokens_a | tokens_b
            if union:
                jaccard = len(tokens_a & tokens_b) / len(union)

        # Sequence matcher on joined tokens
        str_a = " ".join(a.name_tokens)
        str_b = " ".join(b.name_tokens)
        seq_ratio = 0.0
        if str_a and str_b:
            seq_ratio = SequenceMatcher(None, str_a, str_b).ratio()

        # Take the better of the two
        return max(jaccard, seq_ratio)
