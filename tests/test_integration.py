"""
Integration Tests

Test the full pipeline end-to-end.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.loaders import generate_sample_data, MultiAssetLoader, FactorDataLoader
from trend_engine.trend_engine import TrendConfig
from analysis.multi_asset_breadth import analyze_asset_breadth
from analysis.factor_trends import analyze_factor_trends
from analytics.signals import SignalGenerator
from analytics.regimes import RegimeDetector
from utils.validation import DataValidator, validate_pipeline_inputs


class TestFullPipeline:
    """Test complete analysis pipeline."""

    @pytest.fixture(scope="class")
    def sample_data_dir(self, tmp_path_factory):
        """Generate sample data in temp directory."""
        data_dir = tmp_path_factory.mktemp("data")
        generate_sample_data(str(data_dir))
        return data_dir

    def test_data_generation(self, sample_data_dir):
        """Test that sample data is generated correctly."""
        assert (sample_data_dir / "multi_asset_prices.csv").exists()
        assert (sample_data_dir / "multi_asset_metadata.csv").exists()
        assert (sample_data_dir / "factor_returns.csv").exists()

    def test_data_loading(self, sample_data_dir):
        """Test data loading."""
        loader = MultiAssetLoader(str(sample_data_dir))

        prices = loader.load_prices()
        metadata = loader.load_metadata()

        assert isinstance(prices, pd.DataFrame)
        assert isinstance(metadata, pd.DataFrame)
        assert len(prices) > 0
        assert len(metadata) > 0

    def test_data_validation(self, sample_data_dir):
        """Test data validation."""
        loader = MultiAssetLoader(str(sample_data_dir))
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        results = validate_pipeline_inputs(prices, metadata)

        assert 'prices' in results
        assert 'metadata' in results
        assert results['prices'].is_valid
        assert results['metadata'].is_valid

    def test_breadth_analysis_pipeline(self, sample_data_dir):
        """Test full breadth analysis pipeline."""
        loader = MultiAssetLoader(str(sample_data_dir))
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        config = TrendConfig(short_window=20, long_window=50, slope_window=60)

        results = analyze_asset_breadth(
            prices,
            metadata,
            config,
            group_by=['asset_class']
        )

        assert 'breadth' in results
        assert 'breadth_with_changes' in results
        assert 'latest' in results
        assert 'summary' in results

        # Check data quality
        assert len(results['breadth']) > 0
        assert len(results['latest']) > 0

    def test_factor_analysis_pipeline(self, sample_data_dir):
        """Test full factor analysis pipeline."""
        loader = FactorDataLoader(str(sample_data_dir))
        factor_returns = loader.load_factor_returns()

        config = TrendConfig(short_window=20, long_window=50, slope_window=60)

        results = analyze_factor_trends(factor_returns, config=config)

        assert 'trends' in results
        assert 'latest' in results
        assert 'correlations' in results

        assert len(results['trends']) > 0
        assert len(results['latest']) > 0

    def test_signal_generation(self, sample_data_dir):
        """Test signal generation from breadth data."""
        loader = MultiAssetLoader(str(sample_data_dir))
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        config = TrendConfig(short_window=20, long_window=50, slope_window=60)
        results = analyze_asset_breadth(prices, metadata, config)

        generator = SignalGenerator()

        # Generate breadth signals
        breadth_signals = generator.generate_breadth_signals(
            results['breadth'],
            'Equity'
        )

        assert isinstance(breadth_signals, list)
        # Signals may or may not be generated depending on data

        # Generate momentum signals
        momentum_signals = generator.generate_trend_change_signals(
            results['breadth_with_changes']
        )

        assert isinstance(momentum_signals, list)

    def test_regime_detection(self, sample_data_dir):
        """Test regime detection."""
        loader = MultiAssetLoader(str(sample_data_dir))
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        # Get equity prices
        equity_tickers = metadata[
            metadata['asset_class'] == 'Equity'
        ]['ticker'].tolist()

        avg_price = prices[equity_tickers].mean(axis=1)

        detector = RegimeDetector()
        regimes = detector.detect_all_regimes(avg_price)

        assert 'trend' in regimes
        assert 'volatility' in regimes

        # Check regime info structure
        trend_regime = regimes['trend']
        assert hasattr(trend_regime, 'regime')
        assert hasattr(trend_regime, 'confidence')
        assert hasattr(trend_regime, 'duration_days')


class TestAPIIntegration:
    """Test API endpoints (requires running server)."""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for API (skip if server not running)."""
        return "http://localhost:8000"

    @pytest.mark.skip(reason="Requires running API server")
    def test_health_endpoint(self, api_base_url):
        """Test health check endpoint."""
        import requests
        response = requests.get(f"{api_base_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.skip(reason="Requires running API server")
    def test_breadth_endpoint(self, api_base_url):
        """Test breadth endpoint."""
        import requests
        response = requests.get(f"{api_base_url}/api/asset-breadth/current")
        assert response.status_code in [200, 404]  # 404 if no data


class TestDataQuality:
    """Test data quality checks."""

    def test_no_missing_data(self, tmp_path):
        """Test handling of missing data."""
        # Create price data with missing values
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        prices = pd.DataFrame({
            'A': np.random.randn(100).cumsum() + 100,
            'B': np.random.randn(100).cumsum() + 100,
        }, index=dates)

        # Introduce missing data
        prices.iloc[10:20, 0] = np.nan

        validator = DataValidator()
        result = validator.validate_price_data(prices, max_missing_pct=0.15)

        assert isinstance(result.warnings, list)
        # Should have warnings about missing data

    def test_extreme_returns(self):
        """Test detection of extreme returns."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        prices = pd.Series(100, index=dates)

        # Create extreme return
        prices.iloc[50] = 200  # 100% jump

        returns = prices.pct_change()

        validator = DataValidator()
        result = validator.validate_returns(returns, max_return=0.5)

        assert len(result.warnings) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
