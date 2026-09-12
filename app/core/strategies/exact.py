"""
Exact Match Strategy — Strict string equality after normalization.

Returns 1.0 if normalized names are identical, 0.0 otherwise.
Useful as a baseline and for catching trivially identical products.
"""

from app.core.models import NormalizedProduct
from app.core.ports import MatchingStrategy


class ExactMatchStrategy(MatchingStrategy):

    @property
    def strategy_name(self) -> str:
        return "Exact Match"

    @property
    def strategy_id(self) -> str:
        return "exact"

    def compute_similarity(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> float:
        if a.normalized_name == b.normalized_name:
            return 1.0
        return 0.0
