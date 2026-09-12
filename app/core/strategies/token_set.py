"""
Token Set Ratio Strategy — Jaccard similarity on word token sets.

Order-independent: "maggi masala noodles" == "masala noodles maggi".
Handles word reordering well but ignores word-level similarity
(e.g., "minute" vs "min" are different tokens).
"""

from app.core.models import NormalizedProduct
from app.core.ports import MatchingStrategy


class TokenSetRatioStrategy(MatchingStrategy):

    @property
    def strategy_name(self) -> str:
        return "Token Set Ratio"

    @property
    def strategy_id(self) -> str:
        return "token_set"

    def compute_similarity(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> float:
        tokens_a = set(a.name_tokens)
        tokens_b = set(b.name_tokens)

        if not tokens_a and not tokens_b:
            # Both empty token sets — if brands match, consider similar
            return 0.5 if a.brand and a.brand == b.brand else 0.0

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b

        if not union:
            return 0.0

        return len(intersection) / len(union)
