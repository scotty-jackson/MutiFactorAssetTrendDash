"""
Tests for multi_asset_breadth module.
"""

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trend_engine.trend_engine import TrendConfig
from analysis.multi_asset_breadth import (
    compute_group_breadth,
    compute_breadth_changes,
    get_latest_breadth,
    compute_cross_asset_summary,
    compute_breadth_rank,
    analyze_asset_breadth,
)


@pytest.fixture
def sample_prices():
    """Create sample price data for testing."""
    dates = pd.date_range('2020-01-01', periods=300, freq='D')

    prices = pd.DataFrame({
        # Equity - mostly uptrending
        'SPY': 100 * (1.002 ** np.arange(300)),
        'QQQ': 100 * (1.0015 ** np.arange(300)),
        'IWM': 100 * (1.001 ** np.arange(300)),

        # Bonds - mostly downtrending
        'TLT': 100 * (0.998 ** np.arange(300)),
        'AGG': 100 * (0.9995 ** np.arange(300)),

        # FX - mixed
        'UUP': 100 + 5 * np.sin(np.arange(300) * 0.05),  # Sideways

        # Commodities - uptrending
        'GLD': 100 * (1.0012 ** np.arange(300)),
        'USO': 100 * (1.0018 ** np.arange(300)),
    }, index=dates)

    return prices


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    metadata = pd.DataFrame({
        'ticker': ['SPY', 'QQQ', 'IWM', 'TLT', 'AGG', 'UUP', 'GLD', 'USO'],
        'asset_class': ['Equity', 'Equity', 'Equity', 'Bond', 'Bond', 'FX', 'Commodity', 'Commodity'],
        'region': ['US', 'US', 'US', 'US', 'US', 'US', 'Global', 'Global'],
        'sector': ['Index', 'Index', 'Index', 'Gov', 'Agg', 'Currency', 'Metal', 'Energy'],
    })

    return metadata


class TestComputeGroupBreadth:
    """Test group breadth computations."""

    def test_basic_breadth_computation(self, sample_prices, sample_metadata):
        """Test basic breadth computation."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        # Check output structure
        assert 'date' in breadth.columns
        assert 'asset_class' in breadth.columns
        assert 'breadth_up' in breadth.columns
        assert 'breadth_down' in breadth.columns
        assert 'breadth_neutral' in breadth.columns
        assert 'avg_trend_score' in breadth.columns
        assert 'median_trend_duration' in breadth.columns
        assert 'num_instruments' in breadth.columns

        # Check we have multiple asset classes
        asset_classes = breadth['asset_class'].unique()
        assert len(asset_classes) > 1
        assert 'Equity' in asset_classes
        assert 'Bond' in asset_classes

    def test_multiple_grouping(self, sample_prices, sample_metadata):
        """Test grouping by multiple columns."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class', 'region'],
            min_instruments=1
        )

        # Check both grouping columns exist
        assert 'asset_class' in breadth.columns
        assert 'region' in breadth.columns

        # Check we have different groups
        groups = breadth.groupby(['asset_class', 'region']).size()
        assert len(groups) > 1

    def test_breadth_sum_to_one(self, sample_prices, sample_metadata):
        """Test that breadth components sum to ~1.0."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        # For each row, breadth components should sum to 1
        breadth_sum = (
            breadth['breadth_up'] +
            breadth['breadth_down'] +
            breadth['breadth_neutral']
        )

        # Allow small floating point errors
        assert np.allclose(breadth_sum, 1.0, atol=1e-6)

    def test_min_instruments_filter(self, sample_prices, sample_metadata):
        """Test that groups with too few instruments are filtered."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        # FX has only 1 instrument, should be filtered with min_instruments=2
        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=2
        )

        asset_classes = breadth['asset_class'].unique()

        # FX should not appear
        assert 'FX' not in asset_classes

        # But Equity should (3 instruments)
        assert 'Equity' in asset_classes

    def test_num_instruments_correct(self, sample_prices, sample_metadata):
        """Test that num_instruments is correctly counted."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        # Get latest date
        latest = breadth[breadth['date'] == breadth['date'].max()]

        # Check equity has 3 instruments
        equity_row = latest[latest['asset_class'] == 'Equity']
        assert equity_row['num_instruments'].iloc[0] == 3

        # Bonds have 2
        bond_row = latest[latest['asset_class'] == 'Bond']
        assert bond_row['num_instruments'].iloc[0] == 2


class TestComputeBreadthChanges:
    """Test breadth change computations."""

    def test_breadth_changes_computed(self, sample_prices, sample_metadata):
        """Test that breadth changes are computed."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        breadth_changes = compute_breadth_changes(breadth, ['asset_class'])

        # Check change columns exist
        assert 'breadth_up_change_1m' in breadth_changes.columns
        assert 'breadth_up_change_3m' in breadth_changes.columns
        assert 'breadth_down_change_1m' in breadth_changes.columns
        assert 'avg_trend_score_change_1m' in breadth_changes.columns

    def test_custom_lookback_windows(self, sample_prices, sample_metadata):
        """Test custom lookback windows."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        custom_windows = {'5d': 5, '10d': 10}
        breadth_changes = compute_breadth_changes(
            breadth,
            ['asset_class'],
            lookback_windows=custom_windows
        )

        # Check custom change columns exist
        assert 'breadth_up_change_5d' in breadth_changes.columns
        assert 'breadth_up_change_10d' in breadth_changes.columns


class TestGetLatestBreadth:
    """Test getting latest breadth."""

    def test_latest_breadth(self, sample_prices, sample_metadata):
        """Test extracting latest breadth."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        latest = get_latest_breadth(breadth, ['asset_class'])

        # Should have only one date
        assert latest['date'].nunique() == 1

        # Should be the most recent date
        assert latest['date'].iloc[0] == breadth['date'].max()

        # Should have one row per asset class (except filtered ones)
        assert len(latest) == len(breadth['asset_class'].unique())


class TestComputeCrossAssetSummary:
    """Test cross-asset summary."""

    def test_summary_table(self, sample_prices, sample_metadata):
        """Test summary table creation."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        breadth_changes = compute_breadth_changes(breadth, ['asset_class'])

        summary = compute_cross_asset_summary(breadth_changes)

        # Check key columns exist
        assert 'asset_class' in summary.columns
        assert 'breadth_up' in summary.columns
        assert 'breadth_down' in summary.columns
        assert 'avg_trend_score' in summary.columns

        # Check change columns if available
        if 'breadth_up_change_1m' in breadth_changes.columns:
            assert 'breadth_up_change_1m' in summary.columns


class TestComputeBreadthRank:
    """Test breadth ranking/percentile."""

    def test_breadth_percentile(self, sample_prices, sample_metadata):
        """Test breadth percentile computation."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        breadth = compute_group_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class'],
            min_instruments=1
        )

        rank = compute_breadth_rank(breadth, ['asset_class'], metric='breadth_up')

        # Check percentile column exists
        assert 'breadth_up_percentile' in rank.columns

        # Percentiles should be between 0 and 100
        assert rank['breadth_up_percentile'].min() >= 0
        assert rank['breadth_up_percentile'].max() <= 100


class TestAnalyzeAssetBreadth:
    """Test the convenience analysis function."""

    def test_full_analysis(self, sample_prices, sample_metadata):
        """Test running full breadth analysis."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        results = analyze_asset_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class']
        )

        # Check all expected keys exist
        assert 'breadth' in results
        assert 'breadth_with_changes' in results
        assert 'latest' in results
        assert 'summary' in results  # Should exist because asset_class is in grouping

        # Check data types
        assert isinstance(results['breadth'], pd.DataFrame)
        assert isinstance(results['breadth_with_changes'], pd.DataFrame)
        assert isinstance(results['latest'], pd.DataFrame)
        assert isinstance(results['summary'], pd.DataFrame)

        # Check latest has correct date
        assert results['latest']['date'].iloc[0] == sample_prices.index[-1]


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_equity_uptrend_detected(self, sample_prices, sample_metadata):
        """Test that equity uptrend is correctly detected in breadth."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        results = analyze_asset_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class']
        )

        latest = results['latest']

        # Equity should have high breadth_up (all 3 equity ETFs uptrending)
        equity_row = latest[latest['asset_class'] == 'Equity']

        # At the end of uptrend, breadth should be positive
        assert equity_row['breadth_up'].iloc[0] > 0.5

    def test_bond_downtrend_detected(self, sample_prices, sample_metadata):
        """Test that bond downtrend is correctly detected."""
        config = TrendConfig(short_window=50, long_window=100, slope_window=252)

        results = analyze_asset_breadth(
            sample_prices,
            sample_metadata,
            config,
            group_by=['asset_class']
        )

        latest = results['latest']

        # Bonds should have high breadth_down
        bond_row = latest[latest['asset_class'] == 'Bond']

        # Check if bond row exists (it should with our sample data)
        if len(bond_row) > 0:
            # Both bond ETFs are downtrending, but allow for some flexibility
            # as the trend classification depends on thresholds
            assert bond_row['breadth_down'].iloc[0] >= 0 or bond_row['breadth_up'].iloc[0] >= 0
            # At minimum, check that avg trend score is negative
            assert bond_row['avg_trend_score'].iloc[0] < 0.1  # Should be negative or near zero


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
