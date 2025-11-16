"""
Analysis Modules

Modules for computing breadth metrics, factor trends, and valuation spreads.
"""

from .multi_asset_breadth import compute_group_breadth, compute_breadth_changes
from .factor_trends import compute_factor_trends
from .factor_breadth import compute_factor_breadth
from .valuation_spreads import compute_valuation_spreads

__all__ = [
    "compute_group_breadth",
    "compute_breadth_changes",
    "compute_factor_trends",
    "compute_factor_breadth",
    "compute_valuation_spreads",
]
