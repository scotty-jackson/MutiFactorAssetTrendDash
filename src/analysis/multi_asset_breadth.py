"""
Multi Asset Breadth Analysis

Compute breadth metrics across different asset classes, regions, and sectors.
Breadth measures the percentage of instruments in various trend states within
each group.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
import sys
from pathlib import Path

# Import trend engine
sys.path.insert(0, str(Path(__file__).parent.parent))
from trend_engine.trend_engine import (
    TrendConfig,
    compute_all_trend_metrics,
    STATE_NAMES
)


def compute_group_breadth(
    prices: pd.DataFrame,
    instrument_metadata: pd.DataFrame,
    config: Optional[TrendConfig] = None,
    group_by: Optional[List[str]] = None,
    min_instruments: int = 3
) -> pd.DataFrame:
    """
    Compute trend breadth metrics by group.

    Parameters
    ----------
    prices : pd.DataFrame
        Price data with DatetimeIndex and one column per instrument.
        Columns should match instrument identifiers in metadata.
    instrument_metadata : pd.DataFrame
        Metadata for each instrument with columns like:
        - ticker (index or column)
        - asset_class
        - region
        - sector
        - Any other grouping columns
    config : TrendConfig, optional
        Trend engine configuration
    group_by : list of str, optional
        List of columns to group by (e.g., ['asset_class', 'region'])
        If None, will try common groupings
    min_instruments : int
        Minimum number of instruments required for a group to be valid

    Returns
    -------
    breadth_df : pd.DataFrame
        Long format with columns:
        - date
        - group columns (e.g., asset_class, region)
        - breadth_up: % in any uptrend state
        - breadth_down: % in any downtrend state
        - breadth_neutral: % in neutral state
        - breadth_strong_up: % in strong uptrend
        - breadth_strong_down: % in strong downtrend
        - avg_trend_score: average trend score
        - median_trend_score: median trend score
        - median_trend_duration: median trend duration
        - num_instruments: number of instruments in group
    """
    if config is None:
        config = TrendConfig()

    if group_by is None:
        # Try common grouping columns
        group_by = []
        for col in ['asset_class', 'region', 'sector', 'style']:
            if col in instrument_metadata.columns:
                group_by.append(col)

        if len(group_by) == 0:
            raise ValueError(
                "No grouping columns found. Please specify group_by parameter or "
                "include columns like 'asset_class', 'region', 'sector' in metadata."
            )

    # Ensure metadata has ticker as column
    metadata = instrument_metadata.copy()
    if 'ticker' not in metadata.columns:
        metadata = metadata.reset_index()
        if metadata.columns[0] != 'ticker':
            metadata = metadata.rename(columns={metadata.columns[0]: 'ticker'})

    # Filter prices to only include instruments in metadata
    common_tickers = list(set(prices.columns) & set(metadata['ticker']))
    if len(common_tickers) == 0:
        raise ValueError("No common instruments between prices and metadata")

    prices = prices[common_tickers]
    metadata = metadata[metadata['ticker'].isin(common_tickers)]

    # Compute trend metrics for all instruments
    print(f"Computing trend metrics for {len(common_tickers)} instruments...")
    metrics = compute_all_trend_metrics(prices, config)

    trend_scores = metrics['trend_scores']
    trend_states = metrics['trend_states']
    trend_durations = metrics['trend_durations']

    # Prepare data for aggregation
    # Convert to long format
    dates = prices.index

    breadth_results = []

    for date in dates:
        # Get data for this date
        states_today = trend_states.loc[date]
        scores_today = trend_scores.loc[date]
        durations_today = trend_durations.loc[date]

        # Create DataFrame with all data
        daily_data = pd.DataFrame({
            'ticker': states_today.index,
            'state': states_today.values,
            'score': scores_today.values,
            'duration': durations_today.values,
        })

        # Merge with metadata
        daily_data = daily_data.merge(metadata, on='ticker', how='left')

        # Remove NaN states
        daily_data = daily_data[daily_data['state'].notna()]

        if len(daily_data) == 0:
            continue

        # Group and aggregate
        for group_keys, group_df in daily_data.groupby(group_by):
            if len(group_df) < min_instruments:
                continue

            # Ensure group_keys is iterable
            if not isinstance(group_keys, tuple):
                group_keys = (group_keys,)

            # Compute breadth metrics
            total = len(group_df)

            # Count states
            state_counts = group_df['state'].value_counts()

            breadth_strong_down = state_counts.get(0, 0) / total
            breadth_mod_down = state_counts.get(1, 0) / total
            breadth_neutral = state_counts.get(2, 0) / total
            breadth_mod_up = state_counts.get(3, 0) / total
            breadth_strong_up = state_counts.get(4, 0) / total

            # Aggregate breadth
            breadth_up = breadth_mod_up + breadth_strong_up
            breadth_down = breadth_mod_down + breadth_strong_down

            # Summary statistics
            avg_score = group_df['score'].mean()
            median_score = group_df['score'].median()
            median_duration = group_df['duration'].median()

            # Build result row
            result_row = {'date': date}

            # Add group keys
            for i, group_col in enumerate(group_by):
                result_row[group_col] = group_keys[i]

            # Add metrics
            result_row.update({
                'breadth_up': breadth_up,
                'breadth_down': breadth_down,
                'breadth_neutral': breadth_neutral,
                'breadth_strong_up': breadth_strong_up,
                'breadth_strong_down': breadth_strong_down,
                'avg_trend_score': avg_score,
                'median_trend_score': median_score,
                'median_trend_duration': median_duration,
                'num_instruments': total,
            })

            breadth_results.append(result_row)

    if len(breadth_results) == 0:
        raise ValueError("No breadth results computed. Check data and parameters.")

    breadth_df = pd.DataFrame(breadth_results)

    return breadth_df


def compute_breadth_changes(
    breadth_df: pd.DataFrame,
    group_by: List[str],
    lookback_windows: Optional[Dict[str, int]] = None
) -> pd.DataFrame:
    """
    Compute changes in breadth over various lookback windows.

    Parameters
    ----------
    breadth_df : pd.DataFrame
        Output from compute_group_breadth
    group_by : list of str
        Columns that define groups
    lookback_windows : dict, optional
        Dictionary mapping window names to periods.
        Default: {'1m': 21, '3m': 63, '6m': 126, '12m': 252}

    Returns
    -------
    changes_df : pd.DataFrame
        Original breadth_df with additional columns for changes:
        - breadth_up_change_1m
        - breadth_up_change_3m
        - etc.
    """
    if lookback_windows is None:
        lookback_windows = {
            '1m': 21,
            '3m': 63,
            '6m': 126,
            '12m': 252,
        }

    df = breadth_df.copy()

    # Sort by group and date
    sort_cols = group_by + ['date']
    df = df.sort_values(sort_cols)

    # For each metric, compute changes
    metrics_to_diff = ['breadth_up', 'breadth_down', 'avg_trend_score']

    for metric in metrics_to_diff:
        for window_name, window_periods in lookback_windows.items():
            col_name = f'{metric}_change_{window_name}'

            # Compute change within each group
            df[col_name] = df.groupby(group_by)[metric].diff(window_periods)

    return df


def get_latest_breadth(
    breadth_df: pd.DataFrame,
    group_by: List[str]
) -> pd.DataFrame:
    """
    Get the most recent breadth metrics for each group.

    Parameters
    ----------
    breadth_df : pd.DataFrame
        Output from compute_group_breadth or compute_breadth_changes
    group_by : list of str
        Columns that define groups

    Returns
    -------
    latest_df : pd.DataFrame
        Latest breadth metrics for each group
    """
    # Get most recent date
    latest_date = breadth_df['date'].max()

    latest_df = breadth_df[breadth_df['date'] == latest_date].copy()

    return latest_df


def compute_cross_asset_summary(
    breadth_df: pd.DataFrame,
    asset_class_col: str = 'asset_class'
) -> pd.DataFrame:
    """
    Create a summary table of breadth across asset classes.

    Parameters
    ----------
    breadth_df : pd.DataFrame
        Output from compute_breadth_changes
    asset_class_col : str
        Name of the asset class column

    Returns
    -------
    summary_df : pd.DataFrame
        Summary with asset classes as rows and key metrics as columns
    """
    latest = get_latest_breadth(breadth_df, [asset_class_col])

    # Select key columns
    summary_cols = [
        asset_class_col,
        'breadth_up',
        'breadth_down',
        'avg_trend_score',
        'median_trend_duration',
        'num_instruments',
    ]

    # Add change columns if available
    change_cols = [col for col in latest.columns if '_change_' in col]
    summary_cols.extend(change_cols)

    # Filter to available columns
    available_cols = [col for col in summary_cols if col in latest.columns]

    summary_df = latest[available_cols].copy()

    # Round for readability
    numeric_cols = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_cols] = summary_df[numeric_cols].round(3)

    return summary_df


def compute_breadth_rank(
    breadth_df: pd.DataFrame,
    group_by: List[str],
    metric: str = 'breadth_up',
    percentile: bool = True
) -> pd.DataFrame:
    """
    Compute historical percentile or rank of current breadth.

    This helps identify if current breadth is unusually high or low
    relative to history.

    Parameters
    ----------
    breadth_df : pd.DataFrame
        Output from compute_group_breadth
    group_by : list of str
        Columns that define groups
    metric : str
        Metric to rank (e.g., 'breadth_up', 'avg_trend_score')
    percentile : bool
        If True, return percentile (0-100), else return rank

    Returns
    -------
    rank_df : pd.DataFrame
        Latest breadth with historical rank/percentile
    """
    df = breadth_df.copy()

    def compute_percentile(group):
        """Compute percentile for each row within group."""
        group = group.sort_values('date')
        group[f'{metric}_percentile'] = group[metric].rank(pct=True) * 100
        return group

    df = df.groupby(group_by, group_keys=False).apply(compute_percentile)

    latest = get_latest_breadth(df, group_by)

    return latest


# Utility function for quick analysis
def analyze_asset_breadth(
    prices: pd.DataFrame,
    instrument_metadata: pd.DataFrame,
    config: Optional[TrendConfig] = None,
    group_by: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to run full breadth analysis.

    Returns
    -------
    results : dict
        Dictionary with keys:
        - 'breadth': full breadth time series
        - 'breadth_with_changes': breadth with change metrics
        - 'latest': latest breadth for all groups
        - 'summary': summary table (if asset_class is in grouping)
    """
    print("Computing group breadth...")
    breadth = compute_group_breadth(prices, instrument_metadata, config, group_by)

    if group_by is None:
        # Infer from breadth output
        group_by = [col for col in breadth.columns
                   if col not in ['date', 'breadth_up', 'breadth_down', 'breadth_neutral',
                                  'breadth_strong_up', 'breadth_strong_down',
                                  'avg_trend_score', 'median_trend_score',
                                  'median_trend_duration', 'num_instruments']]

    print("Computing breadth changes...")
    breadth_changes = compute_breadth_changes(breadth, group_by)

    print("Getting latest breadth...")
    latest = get_latest_breadth(breadth_changes, group_by)

    results = {
        'breadth': breadth,
        'breadth_with_changes': breadth_changes,
        'latest': latest,
    }

    # Add summary if asset_class is available
    if 'asset_class' in group_by:
        print("Computing cross-asset summary...")
        summary = compute_cross_asset_summary(breadth_changes)
        results['summary'] = summary

    return results
