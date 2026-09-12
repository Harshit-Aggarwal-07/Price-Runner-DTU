"""
Levenshtein Strategy — Character-level edit distance ratio.

Uses Python's built-in difflib.SequenceMatcher (no external deps).
Good for catching abbreviations ("minute" ≈ "min") and typos.
"""

from difflib import SequenceMatcher

from app.core.models import NormalizedProduct
from app.core.ports import MatchingStrategy


class LevenshteinStrategy(MatchingStrategy):

    @property
    def strategy_name(self) -> str:
        return "Sequence Matcher"

    @property
    def strategy_id(self) -> str:
        return "levenshtein"

    def compute_similarity(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> float:
        name_a = " ".join(a.name_tokens)
        name_b = " ".join(b.name_tokens)

        if not name_a and not name_b:
            return 0.5 if a.brand and a.brand == b.brand else 0.0

        if not name_a or not name_b:
            return 0.0

        return SequenceMatcher(None, name_a, name_b).ratio()
