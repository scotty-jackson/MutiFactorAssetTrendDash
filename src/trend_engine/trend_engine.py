"""
Core Trend Engine

This module provides the fundamental building blocks for trend analysis:
- Moving average calculations
- Slope estimation via linear regression
- Trend score computation (weighted combination of metrics)
- Discrete trend state classification
- Trend duration tracking

All functions are designed to work with both single series (pd.Series) and
panel data (pd.DataFrame with MultiIndex).
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Union, Tuple
from dataclasses import dataclass


@dataclass
class TrendConfig:
    """Configuration for trend analysis."""

    # Moving average windows
    short_window: int = 50
    long_window: int = 200

    # Slope window (for linear regression)
    slope_window: int = 252

    # Weights for trend score components
    weight_short_ma: float = 0.4
    weight_long_ma: float = 0.4
    weight_slope: float = 0.2

    # Thresholds for state classification (will be computed from data if None)
    strong_uptrend_threshold: Optional[float] = None
    moderate_uptrend_threshold: Optional[float] = None
    moderate_downtrend_threshold: Optional[float] = None
    strong_downtrend_threshold: Optional[float] = None

    # Whether to use per-instrument thresholds (vs global)
    use_per_instrument_thresholds: bool = False

    # Percentiles for threshold estimation (if thresholds not provided)
    strong_uptrend_percentile: float = 0.90
    moderate_uptrend_percentile: float = 0.60
    moderate_downtrend_percentile: float = 0.40
    strong_downtrend_percentile: float = 0.10

    def __post_init__(self):
        """Validate configuration."""
        assert self.short_window < self.long_window, "short_window must be < long_window"
        assert abs(self.weight_short_ma + self.weight_long_ma + self.weight_slope - 1.0) < 1e-6, \
            "Weights must sum to 1.0"


def compute_moving_averages(
    prices: Union[pd.Series, pd.DataFrame],
    short_window: int = 50,
    long_window: int = 200
) -> Tuple[Union[pd.Series, pd.DataFrame], Union[pd.Series, pd.DataFrame]]:
    """
    Compute simple moving averages.

    Parameters
    ----------
    prices : pd.Series or pd.DataFrame
        Price series. If DataFrame, computes MA for each column.
    short_window : int
        Window for short-term MA (default 50)
    long_window : int
        Window for long-term MA (default 200)

    Returns
    -------
    ma_short, ma_long : Same type as input
        Short and long moving averages
    """
    ma_short = prices.rolling(window=short_window, min_periods=short_window).mean()
    ma_long = prices.rolling(window=long_window, min_periods=long_window).mean()

    return ma_short, ma_long


def compute_slope(
    prices: Union[pd.Series, pd.DataFrame],
    window: int = 252
) -> Union[pd.Series, pd.DataFrame]:
    """
    Compute annualized slope of log prices using rolling linear regression.

    The slope represents the approximate annualized return trend.

    Parameters
    ----------
    prices : pd.Series or pd.DataFrame
        Price series
    window : int
        Rolling window for regression (default 252 for ~1 year of daily data)

    Returns
    -------
    slopes : Same type as input
        Rolling annualized slopes
    """
    log_prices = np.log(prices)

    def rolling_slope(y):
        """Compute slope of linear regression."""
        # When raw=True, y is a numpy array
        if len(y) < window or np.isnan(y).any():
            return np.nan

        x = np.arange(len(y))
        # Demean for numerical stability
        x_mean = x.mean()
        y_mean = y.mean()

        numerator = ((x - x_mean) * (y - y_mean)).sum()
        denominator = ((x - x_mean) ** 2).sum()

        if denominator == 0:
            return np.nan

        slope = numerator / denominator

        # Annualize the slope (multiply by periods per year)
        # This gives approximate annualized log return
        return slope * 252

    if isinstance(log_prices, pd.Series):
        slopes = log_prices.rolling(window=window, min_periods=window).apply(
            rolling_slope, raw=True
        )
    else:
        # For DataFrame, apply to each column
        slopes = log_prices.rolling(window=window, min_periods=window).apply(
            rolling_slope, raw=True
        )

    return slopes


def compute_trend_score(
    prices: Union[pd.Series, pd.DataFrame],
    config: Optional[TrendConfig] = None
) -> Union[pd.Series, pd.DataFrame]:
    """
    Compute trend score as weighted combination of:
    1. Relative distance from short MA
    2. Relative distance from long MA
    3. Annualized slope of log prices

    TrendScore(t) = w1 * (P(t) - MA_short) / MA_short
                    + w2 * (P(t) - MA_long) / MA_long
                    + w3 * slope_of_log_price

    Parameters
    ----------
    prices : pd.Series or pd.DataFrame
        Price series
    config : TrendConfig, optional
        Configuration object with parameters

    Returns
    -------
    trend_scores : Same type as input
        Trend scores aligned with input index
    """
    if config is None:
        config = TrendConfig()

    # Compute components
    ma_short, ma_long = compute_moving_averages(
        prices, config.short_window, config.long_window
    )
    slopes = compute_slope(prices, config.slope_window)

    # Relative distance from MAs
    rel_short = (prices - ma_short) / ma_short
    rel_long = (prices - ma_long) / ma_long

    # Weighted combination
    trend_score = (
        config.weight_short_ma * rel_short +
        config.weight_long_ma * rel_long +
        config.weight_slope * slopes
    )

    return trend_score


def estimate_thresholds_from_data(
    trend_scores: Union[pd.Series, pd.DataFrame],
    config: TrendConfig
) -> Dict[str, float]:
    """
    Estimate trend state thresholds from historical data using percentiles.

    Parameters
    ----------
    trend_scores : pd.Series or pd.DataFrame
        Historical trend scores
    config : TrendConfig
        Configuration with percentile values

    Returns
    -------
    thresholds : dict
        Dictionary with threshold values
    """
    # Flatten to 1D if DataFrame
    if isinstance(trend_scores, pd.DataFrame):
        scores_flat = trend_scores.values.flatten()
        scores_flat = scores_flat[~np.isnan(scores_flat)]
    else:
        scores_flat = trend_scores.dropna().values

    if len(scores_flat) == 0:
        raise ValueError("No valid trend scores to compute thresholds")

    thresholds = {
        'strong_uptrend': np.percentile(scores_flat, config.strong_uptrend_percentile * 100),
        'moderate_uptrend': np.percentile(scores_flat, config.moderate_uptrend_percentile * 100),
        'moderate_downtrend': np.percentile(scores_flat, config.moderate_downtrend_percentile * 100),
        'strong_downtrend': np.percentile(scores_flat, config.strong_downtrend_percentile * 100),
    }

    return thresholds


def classify_trend_state(
    trend_scores: Union[pd.Series, pd.DataFrame],
    config: Optional[TrendConfig] = None,
    thresholds: Optional[Dict[str, float]] = None
) -> Union[pd.Series, pd.DataFrame]:
    """
    Classify continuous trend scores into discrete states.

    States:
    - Strong Uptrend (4)
    - Moderate Uptrend (3)
    - Neutral (2)
    - Moderate Downtrend (1)
    - Strong Downtrend (0)

    Parameters
    ----------
    trend_scores : pd.Series or pd.DataFrame
        Trend scores from compute_trend_score
    config : TrendConfig, optional
        Configuration object
    thresholds : dict, optional
        Explicit thresholds. If None, will use config or estimate from data

    Returns
    -------
    states : Same type as input
        Discrete trend states (0-4) aligned with input index
    """
    if config is None:
        config = TrendConfig()

    # Determine thresholds
    if thresholds is None:
        # Check if config has explicit thresholds
        if config.strong_uptrend_threshold is not None:
            thresholds = {
                'strong_uptrend': config.strong_uptrend_threshold,
                'moderate_uptrend': config.moderate_uptrend_threshold,
                'moderate_downtrend': config.moderate_downtrend_threshold,
                'strong_downtrend': config.strong_downtrend_threshold,
            }
        else:
            # Estimate from data
            thresholds = estimate_thresholds_from_data(trend_scores, config)

    # Classify
    states = pd.Series(2, index=trend_scores.index if isinstance(trend_scores, pd.Series)
                      else trend_scores.index, dtype=int)  # Default to Neutral

    if isinstance(trend_scores, pd.Series):
        scores = trend_scores
        states = pd.Series(2, index=scores.index, dtype=int)

        # Strong downtrend
        states[scores <= thresholds['strong_downtrend']] = 0
        # Moderate downtrend
        states[(scores > thresholds['strong_downtrend']) &
               (scores <= thresholds['moderate_downtrend'])] = 1
        # Neutral (already default)
        # Moderate uptrend
        states[(scores >= thresholds['moderate_uptrend']) &
               (scores < thresholds['strong_uptrend'])] = 3
        # Strong uptrend
        states[scores >= thresholds['strong_uptrend']] = 4

    else:
        # DataFrame - apply to each column
        states = trend_scores.copy()
        for col in trend_scores.columns:
            scores = trend_scores[col]
            col_states = pd.Series(2, index=scores.index, dtype=int)

            col_states[scores <= thresholds['strong_downtrend']] = 0
            col_states[(scores > thresholds['strong_downtrend']) &
                      (scores <= thresholds['moderate_downtrend'])] = 1
            col_states[(scores >= thresholds['moderate_uptrend']) &
                      (scores < thresholds['strong_uptrend'])] = 3
            col_states[scores >= thresholds['strong_uptrend']] = 4

            states[col] = col_states

    return states


def compute_trend_duration(
    states: Union[pd.Series, pd.DataFrame]
) -> Union[pd.Series, pd.DataFrame]:
    """
    Compute the number of consecutive periods in the current trend state.

    For each date, returns how many periods the current state has persisted.

    Parameters
    ----------
    states : pd.Series or pd.DataFrame
        Discrete trend states from classify_trend_state

    Returns
    -------
    durations : Same type as input
        Number of consecutive periods in current state
    """
    def _compute_duration_series(s: pd.Series) -> pd.Series:
        """Compute duration for a single series."""
        if len(s) == 0:
            return pd.Series(dtype=int, index=s.index)

        # Find where state changes
        state_changes = s != s.shift(1)

        # Group by consecutive states
        state_groups = state_changes.cumsum()

        # Count within each group
        durations = s.groupby(state_groups).cumcount() + 1

        return durations

    if isinstance(states, pd.Series):
        return _compute_duration_series(states)
    else:
        # DataFrame - apply to each column
        durations = states.copy()
        for col in states.columns:
            durations[col] = _compute_duration_series(states[col])
        return durations


def compute_all_trend_metrics(
    prices: Union[pd.Series, pd.DataFrame],
    config: Optional[TrendConfig] = None,
    return_thresholds: bool = False
) -> Union[Dict, Tuple[Dict, Dict]]:
    """
    Convenience function to compute all trend metrics at once.

    Parameters
    ----------
    prices : pd.Series or pd.DataFrame
        Price series
    config : TrendConfig, optional
        Configuration object
    return_thresholds : bool
        If True, also return the thresholds used

    Returns
    -------
    metrics : dict
        Dictionary with keys: 'trend_scores', 'trend_states', 'trend_durations',
        'ma_short', 'ma_long', 'slopes'
    thresholds : dict (optional)
        Thresholds used for classification
    """
    if config is None:
        config = TrendConfig()

    # Compute all components
    ma_short, ma_long = compute_moving_averages(
        prices, config.short_window, config.long_window
    )
    slopes = compute_slope(prices, config.slope_window)
    trend_scores = compute_trend_score(prices, config)

    # Estimate thresholds if needed
    thresholds = None
    if config.strong_uptrend_threshold is None:
        thresholds = estimate_thresholds_from_data(trend_scores, config)

    trend_states = classify_trend_state(trend_scores, config, thresholds)
    trend_durations = compute_trend_duration(trend_states)

    metrics = {
        'trend_scores': trend_scores,
        'trend_states': trend_states,
        'trend_durations': trend_durations,
        'ma_short': ma_short,
        'ma_long': ma_long,
        'slopes': slopes,
    }

    if return_thresholds:
        if thresholds is None:
            thresholds = {
                'strong_uptrend': config.strong_uptrend_threshold,
                'moderate_uptrend': config.moderate_uptrend_threshold,
                'moderate_downtrend': config.moderate_downtrend_threshold,
                'strong_downtrend': config.strong_downtrend_threshold,
            }
        return metrics, thresholds

    return metrics


# State name mapping
STATE_NAMES = {
    0: 'Strong Downtrend',
    1: 'Moderate Downtrend',
    2: 'Neutral',
    3: 'Moderate Uptrend',
    4: 'Strong Uptrend',
}


def get_state_name(state_code: int) -> str:
    """Convert numeric state code to human-readable name."""
    return STATE_NAMES.get(state_code, 'Unknown')
