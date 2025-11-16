"""
Factor Breadth Analysis

Compute breadth metrics within factor buckets (e.g., high value vs low value stocks).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from trend_engine.trend_engine import TrendConfig, compute_all_trend_metrics


def compute_factor_breadth(
    stock_prices: pd.DataFrame,
    factor_scores: pd.DataFrame,
    factor_name: str,
    config: Optional[TrendConfig] = None,
    top_quantile: float = 0.1,
    bottom_quantile: float = 0.1,
    rebalance_freq: str = 'M'
) -> pd.DataFrame:
    """
    Compute trend breadth within factor buckets.

    Parameters
    ----------
    stock_prices : pd.DataFrame
        Stock prices with DatetimeIndex, columns are stock identifiers
    factor_scores : pd.DataFrame
        Factor scores with DatetimeIndex and columns are stock identifiers
        Higher scores = more exposure to factor
    factor_name : str
        Name of the factor being analyzed
    config : TrendConfig, optional
        Trend engine configuration
    top_quantile : float
        Top quantile for high factor bucket (default 0.1 = top 10%)
    bottom_quantile : float
        Bottom quantile for low factor bucket (default 0.1 = bottom 10%)
    rebalance_freq : str
        Rebalance frequency ('M' = monthly, 'Q' = quarterly)

    Returns
    -------
    breadth_df : pd.DataFrame
        Long format with columns:
        - date
        - factor
        - bucket ('high' or 'low')
        - breadth_up
        - breadth_down
        - median_trend_duration
        - num_stocks
    """
    if config is None:
        config = TrendConfig()

    # Resample factor scores to rebalance frequency
    rebalance_dates = factor_scores.resample(rebalance_freq).last().index

    results = []

    for rebal_date in rebalance_dates:
        # Get factor scores at rebalance date
        if rebal_date not in factor_scores.index:
            continue

        scores = factor_scores.loc[rebal_date].dropna()

        # Determine high and low buckets
        high_threshold = scores.quantile(1 - top_quantile)
        low_threshold = scores.quantile(bottom_quantile)

        high_stocks = scores[scores >= high_threshold].index.tolist()
        low_stocks = scores[scores <= low_threshold].index.tolist()

        # Get price data from rebalance date forward (until next rebalance)
        next_rebal_idx = rebalance_dates.get_loc(rebal_date) + 1
        if next_rebal_idx < len(rebalance_dates):
            period_end = rebalance_dates[next_rebal_idx]
        else:
            period_end = stock_prices.index[-1]

        period_prices = stock_prices.loc[rebal_date:period_end]

        # Compute trends for high and low buckets
        for bucket_name, bucket_stocks in [('high', high_stocks), ('low', low_stocks)]:
            if len(bucket_stocks) == 0:
                continue

            # Filter to stocks in this bucket that have price data
            available_stocks = [s for s in bucket_stocks if s in period_prices.columns]
            if len(available_stocks) == 0:
                continue

            bucket_prices = period_prices[available_stocks]

            # Compute trend metrics
            try:
                metrics = compute_all_trend_metrics(bucket_prices, config)
                trend_states = metrics['trend_states']
                trend_durations = metrics['trend_durations']

                # Get latest state for each stock in this period
                latest_states = trend_states.iloc[-1]
                latest_durations = trend_durations.iloc[-1]

                # Compute breadth
                total = len(available_stocks)
                breadth_up = ((latest_states >= 3).sum()) / total if total > 0 else 0
                breadth_down = ((latest_states <= 1).sum()) / total if total > 0 else 0
                median_duration = latest_durations.median()

                results.append({
                    'date': rebal_date,
                    'factor': factor_name,
                    'bucket': bucket_name,
                    'breadth_up': breadth_up,
                    'breadth_down': breadth_down,
                    'median_trend_duration': median_duration,
                    'num_stocks': total,
                })
            except Exception as e:
                print(f"Warning: Could not compute trends for {bucket_name} bucket at {rebal_date}: {e}")
                continue

    breadth_df = pd.DataFrame(results)

    # Compute breadth spread (high - low)
    if len(breadth_df) > 0:
        pivot = breadth_df.pivot_table(
            index='date',
            columns='bucket',
            values='breadth_up'
        )

        if 'high' in pivot.columns and 'low' in pivot.columns:
            breadth_df = breadth_df.merge(
                pd.DataFrame({
                    'date': pivot.index,
                    'breadth_spread': pivot['high'] - pivot['low']
                }),
                on='date',
                how='left'
            )

    return breadth_df
