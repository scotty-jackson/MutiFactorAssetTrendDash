"""
Valuation Spreads Analysis

Compute valuation spreads for factor portfolios.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import sys
from pathlib import Path


def compute_valuation_spreads(
    fundamental_data: pd.DataFrame,
    factor_scores: pd.DataFrame,
    factor_name: str,
    valuation_metrics: Optional[List[str]] = None,
    top_quantile: float = 0.1,
    bottom_quantile: float = 0.1,
    rebalance_freq: str = 'M'
) -> pd.DataFrame:
    """
    Compute valuation spreads between factor buckets.

    Parameters
    ----------
    fundamental_data : pd.DataFrame
        Fundamental metrics with MultiIndex (date, stock_id) or columns
        containing valuation metrics (pb, pe, ev_ebitda, etc.)
    factor_scores : pd.DataFrame
        Factor scores with DatetimeIndex, columns are stock identifiers
    factor_name : str
        Name of the factor
    valuation_metrics : list of str, optional
        Metrics to compute spreads for. Default: ['pb', 'pe', 'ev_ebitda']
    top_quantile : float
        Top quantile for expensive bucket
    bottom_quantile : float
        Bottom quantile for cheap bucket
    rebalance_freq : str
        Rebalance frequency

    Returns
    -------
    spreads_df : pd.DataFrame
        Long format with columns:
        - date
        - factor
        - metric (pb, pe, etc.)
        - val_spread (log ratio of medians)
        - val_spread_z (z-score vs history)
        - val_spread_percentile
    """
    if valuation_metrics is None:
        valuation_metrics = ['pb', 'pe', 'ev_ebitda']

    # Resample to rebalance dates
    rebalance_dates = factor_scores.resample(rebalance_freq).last().index

    results = []

    for rebal_date in rebalance_dates:
        if rebal_date not in factor_scores.index:
            continue

        scores = factor_scores.loc[rebal_date].dropna()

        # Determine buckets
        high_threshold = scores.quantile(1 - top_quantile)
        low_threshold = scores.quantile(bottom_quantile)

        high_stocks = scores[scores >= high_threshold].index.tolist()
        low_stocks = scores[scores <= low_threshold].index.tolist()

        # Get fundamental data for this date
        if isinstance(fundamental_data.index, pd.MultiIndex):
            # MultiIndex format
            if rebal_date in fundamental_data.index.get_level_values(0):
                fund_data = fundamental_data.loc[rebal_date]
            else:
                continue
        else:
            # Single index format
            if rebal_date in fundamental_data.index:
                fund_data = fundamental_data.loc[rebal_date]
            else:
                continue

        # Compute spreads for each metric
        for metric in valuation_metrics:
            if metric not in fund_data.columns:
                continue

            # Get median valuations for each bucket
            high_vals = fund_data.loc[fund_data.index.isin(high_stocks), metric].dropna()
            low_vals = fund_data.loc[fund_data.index.isin(low_stocks), metric].dropna()

            if len(high_vals) > 0 and len(low_vals) > 0:
                median_high = high_vals.median()
                median_low = low_vals.median()

                # Compute log spread
                if median_high > 0 and median_low > 0:
                    val_spread = np.log(median_high) - np.log(median_low)

                    results.append({
                        'date': rebal_date,
                        'factor': factor_name,
                        'metric': metric,
                        'val_spread': val_spread,
                        'median_high': median_high,
                        'median_low': median_low,
                    })

    spreads_df = pd.DataFrame(results)

    # Compute z-scores and percentiles vs history
    if len(spreads_df) > 0:
        for metric in spreads_df['metric'].unique():
            metric_data = spreads_df[spreads_df['metric'] == metric].copy()

            # Rolling z-score
            mean_hist = metric_data['val_spread'].expanding().mean()
            std_hist = metric_data['val_spread'].expanding().std()

            z_score = (metric_data['val_spread'] - mean_hist) / std_hist

            # Percentile
            percentile = metric_data['val_spread'].expanding().apply(
                lambda x: (x.iloc[-1] <= x).mean() * 100 if len(x) > 0 else np.nan
            )

            # Update spreads_df
            spreads_df.loc[spreads_df['metric'] == metric, 'val_spread_z'] = z_score.values
            spreads_df.loc[spreads_df['metric'] == metric, 'val_spread_percentile'] = percentile.values

    return spreads_df
