"""
Base Matching Strategy — Abstract interface.

All matching strategies must implement compute_similarity().
"""

from app.core.ports import MatchingStrategy  # Re-export from ports

__all__ = ["MatchingStrategy"]
