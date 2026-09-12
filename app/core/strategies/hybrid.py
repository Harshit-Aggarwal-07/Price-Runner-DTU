"""
Hybrid Gated Strategy — The default, most accurate matching strategy.

Pipeline:
1. Hard Gate: Brand must match (if both have brands). Conflicting brands -> 0.0
2. Hard Gate: Weight & Unit must match identically (same unit, pack count, within ±3% tolerance). Mismatched units -> 0.0
3. Hard Gate: Sub-product / category must not conflict (e.g. noodles vs pasta, white bread vs brown bread) -> 0.0
4. Hard Gate: Product variant must not conflict (e.g. vanilla vs chocolate) -> 0.0
5. Soft Score: Combines token set overlap + sequence matcher ratio
6. Confidence: Strict weighted sum (brand + weight + name + variant)
"""

from difflib import SequenceMatcher
import re
from typing import Optional

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
        Multi-stage confidence scoring with strict gates:
          1. Brand Hard Gate: Both brands must match (or inferred brands match). If different -> 0.0
          2. Weight & Unit Hard Gate: Must have compatible units, pack counts, and weight within tolerance.
             If one has weight and other doesn't, or if weights differ -> 0.0
          3. Sub-product & Category Hard Gate: Specific sub-types must not conflict -> 0.0
          4. Variant Hard Gate: Specific variants must not conflict -> 0.0
          5. Soft Score: Token and sequence similarity
        """
        # ── Gate 1: Brand Compatibility ──
        brand_match = self._check_brand(a, b)
        if brand_match is False:
            return 0.0  # Confirmed different brands -> hard reject

        brand_a = a.brand or self._infer_brand_from_name(a.raw_name)
        brand_b = b.brand or self._infer_brand_from_name(b.raw_name)
        if brand_a and brand_b and brand_a != brand_b:
            return 0.0

        # ── Gate 2: Weight & Unit Strict Gate ──
        if a.weight is not None and b.weight is not None:
            if not a.weight.is_compatible(b.weight, WEIGHT_TOLERANCE_PCT):
                return 0.0  # Different units, pack counts, or weight values -> hard reject
        elif (a.weight is None) != (b.weight is None):
            # One product has weight and the other does not -> cannot guarantee same unit
            return 0.0

        # ── Gate 3: Sub-Product & Category Compatibility ──
        if not self._check_subproduct_compatibility(a, b):
            return 0.0

        # ── Gate 4: Variant Compatibility ──
        if a.variant and b.variant and a.variant != b.variant:
            # Different explicit variants (e.g. Vanilla vs Chocolate, Atta vs Maida)
            return 0.0

        # ── Soft Scoring ──
        confidence = 0.0
        if brand_match is True or (brand_a and brand_b and brand_a == brand_b):
            confidence += 0.35

        if a.weight and b.weight and a.weight.is_compatible(b.weight, WEIGHT_TOLERANCE_PCT):
            confidence += 0.35

        name_score = self._soft_name_score(a, b)
        confidence += name_score * 0.30

        if a.variant and b.variant and a.variant == b.variant:
            confidence = min(1.0, confidence + 0.05)

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

    def _infer_brand_from_name(self, raw_name: str) -> Optional[str]:
        """Infer brand from common multi-word or first-word patterns."""
        lower = raw_name.lower()
        known_multiword_brands = [
            "the health factory", "baker's loaf", "bakers loaf",
            "english oven", "harvest gold", "mother dairy",
            "country delight", "too yumm", "hide & seek", "hide and seek"
        ]
        for kw in known_multiword_brands:
            if kw in lower:
                return kw.replace("'", "").replace("and", "&")
        first_token = re.split(r"[\s\-_|/]", raw_name.strip())[0].lower()
        if len(first_token) > 2:
            return first_token
        return None

    def _check_subproduct_compatibility(self, a: NormalizedProduct, b: NormalizedProduct) -> bool:
        """Prevent distinct sub-products from matching under the same brand."""
        name_a = a.raw_name.lower()
        name_b = b.raw_name.lower()

        # Product form conflicts (e.g. Noodles vs Pasta/Macaroni)
        forms = [
            {"noodles", "noodle"},
            {"pasta", "pazzta", "macaroni", "penne"},
            {"chips", "crisps", "nachos"},
            {"popcorn"},
            {"soup"},
        ]
        for form_group in forms:
            has_a = any(term in name_a for term in form_group)
            has_b = any(term in name_b for term in form_group)
            if has_a != has_b:
                for other_group in forms:
                    if other_group != form_group:
                        if (has_a and any(term in name_b for term in other_group)) or \
                           (has_b and any(term in name_a for term in other_group)):
                            return False

        # Distinct biscuit product lines (Britannia, Parle, Sunfeast)
        biscuit_lines = [
            {"good day"}, {"milk bikis"}, {"bourbon"}, {"dark fantasy"},
            {"krackjack", "krack jack"}, {"marie", "mariegold"}, {"little hearts"},
            {"jim jam"}, {"milano"}, {"parle-g", "parle g"}, {"oreo"},
            {"nutrichoice", "nutri choice"}, {"treat"}, {"nice time", "nice"}
        ]
        for line in biscuit_lines:
            has_a = any(term in name_a for term in line)
            has_b = any(term in name_b for term in line)
            if has_a != has_b:
                for other_line in biscuit_lines:
                    if other_line != line and (
                        (has_a and any(term in name_b for term in other_line)) or
                        (has_b and any(term in name_a for term in other_line))
                    ):
                        return False

        # Distinct cookie / biscuit flavors (e.g. Cashew vs Butter vs Choco Chip)
        cookie_flavors = [
            {"cashew", "kaju"},
            {"butter cookie", "butter cookies", "butter biscuit"},
            {"pista", "pistachio"},
            {"almond", "badam"},
            {"choco chip", "chocochip", "choco chips", "chocolate chip"},
            {"jeera", "cumin"},
            {"ginger"},
            {"cardamom", "elaichi"},
            {"coconut"},
        ]
        for c_flv in cookie_flavors:
            has_a = any(term in name_a for term in c_flv)
            has_b = any(term in name_b for term in c_flv)
            if has_a != has_b:
                for other_c in cookie_flavors:
                    if other_c != c_flv and (
                        (has_a and any(term in name_b for term in other_c)) or
                        (has_b and any(term in name_a for term in other_c))
                    ):
                        return False

        # Distinct milk types (Toned, Double Toned, Full Cream / Gold, Cow, Buffalo)
        milk_types = [
            {"double toned"},
            {"cow milk", "cow"},
            {"buffalo milk", "buffalo"},
            {"full cream", "gold"},
            {"toned milk", "taaza"},
        ]
        for m_type in milk_types:
            has_a = any(term in name_a for term in m_type)
            has_b = any(term in name_b for term in m_type)
            if has_a != has_b:
                for other_m in milk_types:
                    if other_m != m_type and (
                        (has_a and any(term in name_b for term in other_m)) or
                        (has_b and any(term in name_a for term in other_m))
                    ):
                        return False

        # Distinct bread types (White, Brown, Whole Wheat / Atta, Multigrain, Protein)
        bread_types = [
            {"white bread"},
            {"brown bread"},
            {"whole wheat", "wheat bread", "atta bread", "zero maida"},
            {"multigrain", "multi-grain"},
            {"protein bread", "high protein"},
            {"garlic bread"},
            {"pav", "bun", "burger bun"},
            {"sourdough"},
            {"brioche"},
            {"fruit bread", "sweet bread"},
        ]
        for b_type in bread_types:
            has_a = any(term in name_a for term in b_type)
            has_b = any(term in name_b for term in b_type)
            if has_a != has_b:
                for other_b in bread_types:
                    if other_b != b_type and (
                        (has_a and any(term in name_b for term in other_b)) or
                        (has_b and any(term in name_a for term in other_b))
                    ):
                        return False

        return True

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
