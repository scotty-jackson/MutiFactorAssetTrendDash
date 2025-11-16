"""
Tests for trend_engine module.

Tests include:
- Moving average calculations
- Slope computations
- Trend score calculations
- State classification with synthetic data
- Duration tracking
"""

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trend_engine.trend_engine import (
    TrendConfig,
    compute_moving_averages,
    compute_slope,
    compute_trend_score,
    classify_trend_state,
    compute_trend_duration,
    compute_all_trend_metrics,
    estimate_thresholds_from_data,
    get_state_name,
)


class TestMovingAverages:
    """Test moving average calculations."""

    def test_simple_ma_series(self):
        """Test MA on a simple series."""
        # Create simple uptrending series
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(range(1, 301), index=dates)

        ma_short, ma_long = compute_moving_averages(prices, short_window=10, long_window=20)

        # Check that MAs are computed
        assert ma_short.notna().sum() > 0
        assert ma_long.notna().sum() > 0

        # MA should be less than current price in uptrend
        assert prices.iloc[-1] > ma_short.iloc[-1]
        assert prices.iloc[-1] > ma_long.iloc[-1]

        # Short MA should be closer to price than long MA
        assert abs(prices.iloc[-1] - ma_short.iloc[-1]) < abs(prices.iloc[-1] - ma_long.iloc[-1])

    def test_ma_dataframe(self):
        """Test MA on DataFrame with multiple series."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.DataFrame({
            'asset1': range(1, 301),
            'asset2': range(100, 400),
        }, index=dates)

        ma_short, ma_long = compute_moving_averages(prices, short_window=10, long_window=20)

        assert isinstance(ma_short, pd.DataFrame)
        assert isinstance(ma_long, pd.DataFrame)
        assert list(ma_short.columns) == ['asset1', 'asset2']
        assert list(ma_long.columns) == ['asset1', 'asset2']


class TestSlope:
    """Test slope computations."""

    def test_slope_uptrend(self):
        """Test slope on clear uptrend."""
        # Exponential growth
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (1.001 ** np.arange(300)), index=dates)

        slopes = compute_slope(prices, window=252)

        # Should have positive slopes
        valid_slopes = slopes.dropna()
        assert len(valid_slopes) > 0
        assert valid_slopes.mean() > 0

    def test_slope_downtrend(self):
        """Test slope on clear downtrend."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (0.999 ** np.arange(300)), index=dates)

        slopes = compute_slope(prices, window=252)

        valid_slopes = slopes.dropna()
        assert len(valid_slopes) > 0
        assert valid_slopes.mean() < 0

    def test_slope_flat(self):
        """Test slope on flat series."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100, index=dates)

        slopes = compute_slope(prices, window=252)

        valid_slopes = slopes.dropna()
        assert len(valid_slopes) > 0
        # Should be very close to zero
        assert abs(valid_slopes.mean()) < 0.01


class TestTrendScore:
    """Test trend score calculations."""

    def test_trend_score_uptrend(self):
        """Test trend score on uptrending series."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (1.002 ** np.arange(300)), index=dates)

        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        trend_scores = compute_trend_score(prices, config)

        # Should have positive trend scores
        valid_scores = trend_scores.dropna()
        assert len(valid_scores) > 0
        assert valid_scores.iloc[-50:].mean() > 0

    def test_trend_score_downtrend(self):
        """Test trend score on downtrending series."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (0.998 ** np.arange(300)), index=dates)

        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        trend_scores = compute_trend_score(prices, config)

        valid_scores = trend_scores.dropna()
        assert len(valid_scores) > 0
        assert valid_scores.iloc[-50:].mean() < 0

    def test_trend_score_weights_sum_to_one(self):
        """Test that config validates weights sum to 1."""
        with pytest.raises(AssertionError):
            TrendConfig(weight_short_ma=0.5, weight_long_ma=0.5, weight_slope=0.5)


class TestStateClassification:
    """Test trend state classification."""

    def test_classify_strong_uptrend(self):
        """Test classification of strong uptrend."""
        # Create very positive trend scores
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        trend_scores = pd.Series(np.linspace(0.5, 2.0, 100), index=dates)

        # Use explicit thresholds
        thresholds = {
            'strong_uptrend': 1.5,
            'moderate_uptrend': 0.5,
            'moderate_downtrend': -0.5,
            'strong_downtrend': -1.5,
        }

        states = classify_trend_state(trend_scores, thresholds=thresholds)

        # Last values should be strong uptrend (4)
        assert states.iloc[-10:].mean() == 4

    def test_classify_strong_downtrend(self):
        """Test classification of strong downtrend."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        trend_scores = pd.Series(np.linspace(-2.0, -0.5, 100), index=dates)

        thresholds = {
            'strong_uptrend': 1.5,
            'moderate_uptrend': 0.5,
            'moderate_downtrend': -0.5,
            'strong_downtrend': -1.5,
        }

        states = classify_trend_state(trend_scores, thresholds=thresholds)

        # First values should be strong downtrend (0)
        assert states.iloc[:10].mean() == 0

    def test_classify_neutral(self):
        """Test classification of neutral trend."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        trend_scores = pd.Series(np.zeros(100), index=dates)

        thresholds = {
            'strong_uptrend': 1.5,
            'moderate_uptrend': 0.5,
            'moderate_downtrend': -0.5,
            'strong_downtrend': -1.5,
        }

        states = classify_trend_state(trend_scores, thresholds=thresholds)

        # All should be neutral (2)
        assert (states == 2).all()

    def test_estimate_thresholds(self):
        """Test threshold estimation from data."""
        # Create trend scores with known distribution
        np.random.seed(42)
        trend_scores = pd.Series(np.random.randn(1000))

        config = TrendConfig(
            strong_uptrend_percentile=0.90,
            moderate_uptrend_percentile=0.60,
            moderate_downtrend_percentile=0.40,
            strong_downtrend_percentile=0.10,
        )

        thresholds = estimate_thresholds_from_data(trend_scores, config)

        # Check that thresholds are in expected order
        assert thresholds['strong_downtrend'] < thresholds['moderate_downtrend']
        assert thresholds['moderate_downtrend'] < thresholds['moderate_uptrend']
        assert thresholds['moderate_uptrend'] < thresholds['strong_uptrend']

        # Check approximate percentile values
        assert thresholds['strong_uptrend'] > 1.0  # ~90th percentile of standard normal
        assert thresholds['strong_downtrend'] < -1.0  # ~10th percentile


class TestTrendDuration:
    """Test trend duration calculations."""

    def test_duration_constant_state(self):
        """Test duration when state doesn't change."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        states = pd.Series(4, index=dates)  # All strong uptrend

        durations = compute_trend_duration(states)

        # Should increase linearly
        assert durations.iloc[0] == 1
        assert durations.iloc[-1] == 100

    def test_duration_with_changes(self):
        """Test duration with state changes."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')

        # First 50 days uptrend, then 50 days downtrend
        states = pd.Series([4] * 50 + [0] * 50, index=dates)

        durations = compute_trend_duration(states)

        # Check durations
        assert durations.iloc[49] == 50  # Last day of first regime
        assert durations.iloc[50] == 1   # First day of second regime
        assert durations.iloc[-1] == 50  # Last day of second regime

    def test_duration_dataframe(self):
        """Test duration on DataFrame."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        states = pd.DataFrame({
            'asset1': [4] * 50 + [0] * 50,
            'asset2': [4] * 100,
        }, index=dates)

        durations = compute_trend_duration(states)

        assert isinstance(durations, pd.DataFrame)
        assert durations['asset1'].iloc[49] == 50
        assert durations['asset2'].iloc[-1] == 100


class TestComputeAllMetrics:
    """Test the convenience function that computes all metrics."""

    def test_compute_all_metrics_series(self):
        """Test computing all metrics for a series."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (1.001 ** np.arange(300)), index=dates)

        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        metrics = compute_all_trend_metrics(prices, config)

        # Check all expected keys are present
        expected_keys = ['trend_scores', 'trend_states', 'trend_durations',
                        'ma_short', 'ma_long', 'slopes']
        assert set(metrics.keys()) == set(expected_keys)

        # Check types
        assert isinstance(metrics['trend_scores'], pd.Series)
        assert isinstance(metrics['trend_states'], pd.Series)
        assert isinstance(metrics['trend_durations'], pd.Series)

    def test_compute_all_metrics_with_thresholds(self):
        """Test computing all metrics and returning thresholds."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')
        prices = pd.Series(100 * (1.001 ** np.arange(300)), index=dates)

        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        metrics, thresholds = compute_all_trend_metrics(prices, config, return_thresholds=True)

        assert isinstance(thresholds, dict)
        assert 'strong_uptrend' in thresholds
        assert 'moderate_uptrend' in thresholds
        assert 'moderate_downtrend' in thresholds
        assert 'strong_downtrend' in thresholds


class TestStateNames:
    """Test state name mapping."""

    def test_get_state_name(self):
        """Test state name retrieval."""
        assert get_state_name(0) == 'Strong Downtrend'
        assert get_state_name(1) == 'Moderate Downtrend'
        assert get_state_name(2) == 'Neutral'
        assert get_state_name(3) == 'Moderate Uptrend'
        assert get_state_name(4) == 'Strong Uptrend'
        assert get_state_name(99) == 'Unknown'


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_bull_to_bear_transition(self):
        """Test full pipeline on bull-to-bear market transition."""
        # Create synthetic data: bull market then bear market
        dates = pd.date_range('2020-01-01', periods=500, freq='D')

        # Bull market: first 300 days
        bull_prices = 100 * (1.002 ** np.arange(300))
        # Bear market: next 200 days
        bear_prices = bull_prices[-1] * (0.998 ** np.arange(200))

        prices = pd.Series(
            np.concatenate([bull_prices, bear_prices]),
            index=dates
        )

        # Compute all metrics
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        metrics = compute_all_trend_metrics(prices, config)

        # In bull market (near day 290), should have positive trend
        bull_idx = 290
        assert metrics['trend_scores'].iloc[bull_idx] > 0
        assert metrics['trend_states'].iloc[bull_idx] >= 3  # At least moderate uptrend

        # In bear market (near end), should have negative trend
        bear_idx = -10
        assert metrics['trend_scores'].iloc[bear_idx] < 0
        # State might vary but trend score should be negative

    def test_multiple_assets(self):
        """Test with multiple assets (DataFrame)."""
        dates = pd.date_range('2020-01-01', periods=300, freq='D')

        prices = pd.DataFrame({
            'uptrend_asset': 100 * (1.002 ** np.arange(300)),
            'downtrend_asset': 100 * (0.998 ** np.arange(300)),
            'sideways_asset': 100 + 5 * np.sin(np.arange(300) * 0.1),
        }, index=dates)

        config = TrendConfig(short_window=50, long_window=100, slope_window=252)
        metrics = compute_all_trend_metrics(prices, config)

        # Check that each asset has different trend characteristics
        trend_scores = metrics['trend_scores']

        # Uptrend asset should have positive scores
        assert trend_scores['uptrend_asset'].iloc[-50:].mean() > 0

        # Downtrend asset should have negative scores
        assert trend_scores['downtrend_asset'].iloc[-50:].mean() < 0

        # Sideways asset should have scores near zero
        assert abs(trend_scores['sideways_asset'].iloc[-50:].mean()) < 0.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
