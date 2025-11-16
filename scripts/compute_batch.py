"""
Batch Computation Script

Computes all metrics and saves to cache for API serving.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trend_engine.trend_engine import TrendConfig
from analysis.multi_asset_breadth import analyze_asset_breadth
from analysis.factor_trends import analyze_factor_trends
from data.loaders import MultiAssetLoader, FactorDataLoader
from config import DEFAULT_CONFIG


def compute_all_metrics():
    """Run all computations and save results."""

    print("="*80)
    print("Multi Asset Factor Dashboard - Batch Computation")
    print("="*80)

    # Create cache directory
    cache_dir = Path(DEFAULT_CONFIG.data.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize loaders
    multi_asset_loader = MultiAssetLoader(DEFAULT_CONFIG.data.raw_data_dir)
    factor_loader = FactorDataLoader(DEFAULT_CONFIG.data.raw_data_dir)

    # Create trend config
    trend_config = TrendConfig(
        short_window=DEFAULT_CONFIG.trend_engine.short_window,
        long_window=DEFAULT_CONFIG.trend_engine.long_window,
        slope_window=DEFAULT_CONFIG.trend_engine.slope_window,
        weight_short_ma=DEFAULT_CONFIG.trend_engine.weight_short_ma,
        weight_long_ma=DEFAULT_CONFIG.trend_engine.weight_long_ma,
        weight_slope=DEFAULT_CONFIG.trend_engine.weight_slope,
    )

    # 1. Compute Asset Breadth
    print("\n" + "="*80)
    print("1. Computing Multi-Asset Breadth")
    print("="*80)

    try:
        prices = multi_asset_loader.load_prices()
        metadata = multi_asset_loader.load_metadata()

        print(f"Loaded {len(prices.columns)} instruments with {len(prices)} days of data")

        breadth_results = analyze_asset_breadth(
            prices,
            metadata,
            config=trend_config,
            group_by=['asset_class']
        )

        # Save results
        breadth_results['breadth_with_changes'].to_parquet(
            cache_dir / "asset_breadth_full.parquet"
        )
        breadth_results['latest'].to_parquet(
            cache_dir / "asset_breadth_latest.parquet"
        )
        breadth_results['summary'].to_parquet(
            cache_dir / "asset_breadth_summary.parquet"
        )

        print(f"✓ Asset breadth computed and saved to {cache_dir}")
        print(f"  - Latest breadth: {len(breadth_results['latest'])} groups")

    except Exception as e:
        print(f"✗ Error computing asset breadth: {e}")

    # 2. Compute Factor Trends
    print("\n" + "="*80)
    print("2. Computing Factor Trends")
    print("="*80)

    try:
        factor_returns = factor_loader.load_factor_returns()

        print(f"Loaded {len(factor_returns.columns)} factors with {len(factor_returns)} periods")

        factor_results = analyze_factor_trends(
            factor_returns,
            market_returns=None,
            config=trend_config
        )

        # Save results
        factor_results['trends'].to_parquet(
            cache_dir / "factor_trends_full.parquet"
        )
        factor_results['latest'].to_parquet(
            cache_dir / "factor_trends_latest.parquet"
        )
        factor_results['correlations'].to_parquet(
            cache_dir / "factor_correlations.parquet"
        )

        print(f"✓ Factor trends computed and saved to {cache_dir}")
        print(f"  - Factors analyzed: {list(factor_returns.columns)}")

    except Exception as e:
        print(f"✗ Error computing factor trends: {e}")

    print("\n" + "="*80)
    print("Batch computation complete!")
    print("="*80)
    print(f"\nResults saved to: {cache_dir}")
    print("\nYou can now start the API server:")
    print("  cd src/backend && python main.py")
    print("\nOr with uvicorn:")
    print("  uvicorn src.backend.main:app --reload")


if __name__ == "__main__":
    compute_all_metrics()
