"""
Factor Trends Analysis

Analyze trends in factor index returns (Fama-French style).
Converts factor returns to cumulative indices and applies trend analysis.
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
    get_state_name
)


def returns_to_index(
    returns: Union[pd.Series, pd.DataFrame],
    start_value: float = 100.0
) -> Union[pd.Series, pd.DataFrame]:
    """
    Convert return series to cumulative index.

    Parameters
    ----------
    returns : pd.Series or pd.DataFrame
        Return series (e.g., daily or monthly factor returns)
        Can be decimal (0.01 for 1%) or percentage (1.0 for 1%)
    start_value : float
        Starting index value (default 100)

    Returns
    -------
    index : Same type as input
        Cumulative index starting at start_value
    """
    # Detect if returns are in percentage (> 1) or decimal form
    # Heuristic: if median absolute return > 1, assume percentage
    if isinstance(returns, pd.Series):
        median_abs = returns.abs().median()
    else:
        median_abs = returns.abs().median().median()

    if median_abs > 1:
        # Convert percentage to decimal
        returns = returns / 100.0

    # Compute cumulative product of (1 + return)
    cum_index = start_value * (1 + returns).cumprod()

    return cum_index


def compute_factor_trends(
    factor_returns: pd.DataFrame,
    market_returns: Optional[pd.Series] = None,
    config: Optional[TrendConfig] = None,
    excess_return_windows: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Compute trend metrics for factor indices.

    Parameters
    ----------
    factor_returns : pd.DataFrame
        Factor returns with DatetimeIndex and one column per factor
        (e.g., HML, SMB, MOM, RMW, CMA)
    market_returns : pd.Series, optional
        Market return series for computing excess returns
        If None, will use absolute factor returns
    config : TrendConfig, optional
        Trend engine configuration
    excess_return_windows : list of int, optional
        Windows (in periods) for computing rolling excess returns
        Default: [63, 126, 252] (roughly 3m, 6m, 12m for daily data)

    Returns
    -------
    factor_trends_df : pd.DataFrame
        Long format with columns:
        - date
        - factor (factor name)
        - index_level (cumulative index value)
        - trend_score
        - trend_state
        - trend_state_name
        - trend_duration
        - rolling_Xm_return (rolling returns for various windows)
        - rolling_Xm_excess_return (if market_returns provided)
    """
    if config is None:
        config = TrendConfig()

    if excess_return_windows is None:
        excess_return_windows = [63, 126, 252]  # ~3m, 6m, 12m

    # Convert returns to indices
    print(f"Converting {len(factor_returns.columns)} factor returns to indices...")
    factor_indices = returns_to_index(factor_returns)

    # Compute trend metrics for all factors
    print("Computing trend metrics for factor indices...")
    metrics = compute_all_trend_metrics(factor_indices, config)

    trend_scores = metrics['trend_scores']
    trend_states = metrics['trend_states']
    trend_durations = metrics['trend_durations']

    # Prepare result in long format
    results = []

    for date in factor_indices.index:
        for factor in factor_indices.columns:
            row = {
                'date': date,
                'factor': factor,
                'index_level': factor_indices.loc[date, factor],
                'trend_score': trend_scores.loc[date, factor],
                'trend_state': trend_states.loc[date, factor],
                'trend_duration': trend_durations.loc[date, factor],
            }

            # Add state name
            if pd.notna(row['trend_state']):
                row['trend_state_name'] = get_state_name(int(row['trend_state']))
            else:
                row['trend_state_name'] = 'Unknown'

            results.append(row)

    factor_trends_df = pd.DataFrame(results)

    # Compute rolling returns for each factor
    print("Computing rolling returns...")
    for window in excess_return_windows:
        # Convert window to readable name
        if window <= 21:
            window_name = f'{window}d'
        elif window <= 63:
            window_name = f'{window//21}m'
        else:
            window_name = f'{window//21}m'

        # Compute rolling returns for each factor
        for factor in factor_indices.columns:
            # Rolling return = (current / previous) - 1
            rolling_ret = factor_indices[factor].pct_change(window)

            # Merge into results
            rolling_ret_df = pd.DataFrame({
                'date': rolling_ret.index,
                'factor': factor,
                f'rolling_{window_name}_return': rolling_ret.values
            })

            factor_trends_df = factor_trends_df.merge(
                rolling_ret_df,
                on=['date', 'factor'],
                how='left'
            )

    # Compute excess returns if market provided
    if market_returns is not None:
        print("Computing excess returns vs market...")
        market_index = returns_to_index(market_returns)

        for window in excess_return_windows:
            if window <= 21:
                window_name = f'{window}d'
            elif window <= 63:
                window_name = f'{window//21}m'
            else:
                window_name = f'{window//21}m'

            # Market rolling return
            market_rolling_ret = market_index.pct_change(window)

            for factor in factor_indices.columns:
                factor_rolling_ret = factor_indices[factor].pct_change(window)

                # Excess return = factor return - market return
                excess_ret = factor_rolling_ret - market_rolling_ret

                # Merge into results
                excess_ret_df = pd.DataFrame({
                    'date': excess_ret.index,
                    'factor': factor,
                    f'rolling_{window_name}_excess_return': excess_ret.values
                })

                factor_trends_df = factor_trends_df.merge(
                    excess_ret_df,
                    on=['date', 'factor'],
                    how='left'
                )

    return factor_trends_df


def get_latest_factor_trends(
    factor_trends_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Get the most recent trend state for each factor.

    Parameters
    ----------
    factor_trends_df : pd.DataFrame
        Output from compute_factor_trends

    Returns
    -------
    latest_df : pd.DataFrame
        Latest trend metrics for each factor
    """
    latest_date = factor_trends_df['date'].max()
    latest_df = factor_trends_df[factor_trends_df['date'] == latest_date].copy()

    return latest_df


def compute_factor_regime_history(
    factor_trends_df: pd.DataFrame,
    factor_name: str
) -> pd.DataFrame:
    """
    Compute regime change history for a specific factor.

    Parameters
    ----------
    factor_trends_df : pd.DataFrame
        Output from compute_factor_trends
    factor_name : str
        Name of the factor to analyze

    Returns
    -------
    regime_history : pd.DataFrame
        DataFrame with regime change points:
        - start_date
        - end_date
        - regime (trend_state_name)
        - duration_days
        - return (cumulative return during regime)
    """
    factor_data = factor_trends_df[factor_trends_df['factor'] == factor_name].copy()
    factor_data = factor_data.sort_values('date')

    # Find regime changes
    factor_data['regime_change'] = factor_data['trend_state'] != factor_data['trend_state'].shift(1)

    # Group by regime
    factor_data['regime_group'] = factor_data['regime_change'].cumsum()

    regimes = []

    for regime_id, group in factor_data.groupby('regime_group'):
        if len(group) == 0:
            continue

        start_date = group['date'].iloc[0]
        end_date = group['date'].iloc[-1]
        regime_state = group['trend_state_name'].iloc[0]
        duration = len(group)

        # Compute return during regime
        start_level = group['index_level'].iloc[0]
        end_level = group['index_level'].iloc[-1]
        regime_return = (end_level / start_level) - 1

        regimes.append({
            'start_date': start_date,
            'end_date': end_date,
            'regime': regime_state,
            'duration_days': duration,
            'return': regime_return,
        })

    regime_history = pd.DataFrame(regimes)

    return regime_history


def compute_factor_correlations(
    factor_trends_df: pd.DataFrame,
    metric: str = 'trend_score',
    window: Optional[int] = None
) -> pd.DataFrame:
    """
    Compute correlation matrix of factor trend metrics.

    Useful for understanding which factors tend to trend together.

    Parameters
    ----------
    factor_trends_df : pd.DataFrame
        Output from compute_factor_trends
    metric : str
        Metric to correlate (e.g., 'trend_score', 'trend_state')
    window : int, optional
        If provided, compute rolling correlation over this window

    Returns
    -------
    correlation_matrix : pd.DataFrame
        Factor x Factor correlation matrix
    """
    # Pivot to wide format
    pivot_df = factor_trends_df.pivot(index='date', columns='factor', values=metric)

    if window is None:
        # Full period correlation
        corr_matrix = pivot_df.corr()
    else:
        # Rolling correlation (return the most recent)
        corr_matrix = pivot_df.rolling(window).corr().iloc[-len(pivot_df.columns):]

    return corr_matrix


def analyze_factor_trends(
    factor_returns: pd.DataFrame,
    market_returns: Optional[pd.Series] = None,
    config: Optional[TrendConfig] = None
) -> Dict[str, pd.DataFrame]:
    """
    Convenience function for complete factor trend analysis.

    Returns
    -------
    results : dict
        Dictionary with keys:
        - 'trends': full time series of factor trends
        - 'latest': latest trend state for each factor
        - 'correlations': correlation matrix of trend scores
        - 'regime_history_FACTOR': regime history for each factor
    """
    print("Computing factor trends...")
    trends = compute_factor_trends(factor_returns, market_returns, config)

    print("Getting latest trends...")
    latest = get_latest_factor_trends(trends)

    print("Computing correlations...")
    correlations = compute_factor_correlations(trends, metric='trend_score')

    results = {
        'trends': trends,
        'latest': latest,
        'correlations': correlations,
    }

    # Add regime history for each factor
    print("Computing regime histories...")
    for factor in factor_returns.columns:
        regime_hist = compute_factor_regime_history(trends, factor)
        results[f'regime_history_{factor}'] = regime_hist

    return results


def load_fama_french_factors(
    filepath: str,
    factor_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Load Fama-French factor data from CSV.

    Expected format:
    - Date column (will be parsed as index)
    - Factor return columns (e.g., Mkt-RF, SMB, HML, RMW, CMA, Mom)

    Parameters
    ----------
    filepath : str
        Path to CSV file
    factor_columns : list of str, optional
        Specific factor columns to load. If None, loads all except date and RF

    Returns
    -------
    factor_returns : pd.DataFrame
        Factor returns with DatetimeIndex
    """
    # Load data
    df = pd.read_csv(filepath)

    # Try to identify date column
    date_cols = [col for col in df.columns if 'date' in col.lower()]
    if len(date_cols) > 0:
        date_col = date_cols[0]
    else:
        # Assume first column is date
        date_col = df.columns[0]

    # Parse dates
    df[date_col] = pd.to_datetime(df[date_col], format='%Y%m%d', errors='coerce')

    # Set as index
    df = df.set_index(date_col)
    df.index.name = 'date'

    # Select factor columns
    if factor_columns is not None:
        df = df[factor_columns]
    else:
        # Remove RF (risk-free rate) if present
        if 'RF' in df.columns:
            df = df.drop(columns=['RF'])

    return df
