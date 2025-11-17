"""
Regime Detection API Endpoints

Serve market regime analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analytics.regimes import RegimeDetector
from data.loaders import MultiAssetLoader
from config import DEFAULT_CONFIG

router = APIRouter(prefix="/api/regimes", tags=["regimes"])

CACHE_DIR = Path(DEFAULT_CONFIG.data.cache_dir)


@router.get("/current")
def get_current_regimes(
    asset_class: Optional[str] = Query(default="Equity")
):
    """
    Get current market regimes.

    Parameters:
    - asset_class: Asset class to analyze (default: Equity)
    """
    try:
        # Load price data
        loader = MultiAssetLoader(DEFAULT_CONFIG.data.raw_data_dir)
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        # Filter to asset class
        tickers_in_class = metadata[
            metadata['asset_class'] == asset_class
        ]['ticker'].tolist()

        if len(tickers_in_class) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No instruments found for asset class: {asset_class}"
            )

        # Use average of all instruments in class
        class_prices = prices[tickers_in_class]
        avg_price = class_prices.mean(axis=1)

        # Detect regimes
        detector = RegimeDetector()
        regimes = detector.detect_all_regimes(avg_price)

        # Convert to dict
        regime_summary = RegimeDetector.regime_summary(regimes)

        return {
            "asset_class": asset_class,
            "regimes": regime_summary.to_dict(orient="records"),
            "as_of_date": avg_price.index[-1].isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
def get_trend_regime(
    asset_class: str = Query(default="Equity")
):
    """Get trend regime (bull/bear/sideways) for an asset class."""
    try:
        loader = MultiAssetLoader(DEFAULT_CONFIG.data.raw_data_dir)
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        tickers_in_class = metadata[
            metadata['asset_class'] == asset_class
        ]['ticker'].tolist()

        if len(tickers_in_class) == 0:
            raise HTTPException(status_code=404, detail="Asset class not found")

        avg_price = prices[tickers_in_class].mean(axis=1)

        detector = RegimeDetector()
        regime_info = detector.detect_trend_regime(avg_price)

        return {
            "asset_class": asset_class,
            "regime": regime_info.regime.value,
            "confidence": regime_info.confidence,
            "start_date": regime_info.start_date.isoformat(),
            "duration_days": regime_info.duration_days,
            "indicators": regime_info.indicators
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatility")
def get_volatility_regime(
    asset_class: str = Query(default="Equity")
):
    """Get volatility regime (high/low vol) for an asset class."""
    try:
        loader = MultiAssetLoader(DEFAULT_CONFIG.data.raw_data_dir)
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        tickers_in_class = metadata[
            metadata['asset_class'] == asset_class
        ]['ticker'].tolist()

        if len(tickers_in_class) == 0:
            raise HTTPException(status_code=404, detail="Asset class not found")

        avg_price = prices[tickers_in_class].mean(axis=1)
        returns = avg_price.pct_change()

        detector = RegimeDetector()
        regime_info = detector.detect_volatility_regime(returns)

        return {
            "asset_class": asset_class,
            "regime": regime_info.regime.value,
            "confidence": regime_info.confidence,
            "start_date": regime_info.start_date.isoformat(),
            "duration_days": regime_info.duration_days,
            "indicators": regime_info.indicators
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk")
def get_risk_regime():
    """Get risk-on/risk-off regime based on equity-bond dynamics."""
    try:
        loader = MultiAssetLoader(DEFAULT_CONFIG.data.raw_data_dir)
        prices = loader.load_prices()
        metadata = loader.load_metadata()

        # Get equity tickers
        equity_tickers = metadata[
            metadata['asset_class'] == 'Equity'
        ]['ticker'].tolist()

        # Get bond tickers
        bond_tickers = metadata[
            metadata['asset_class'] == 'Bond'
        ]['ticker'].tolist()

        if len(equity_tickers) == 0 or len(bond_tickers) == 0:
            raise HTTPException(
                status_code=404,
                detail="Equity or Bond data not available"
            )

        equity_prices = prices[equity_tickers].mean(axis=1)
        bond_prices = prices[bond_tickers].mean(axis=1)

        equity_returns = equity_prices.pct_change()
        bond_returns = bond_prices.pct_change()

        detector = RegimeDetector()
        regime_info = detector.detect_risk_regime(equity_returns, bond_returns)

        return {
            "regime": regime_info.regime.value,
            "confidence": regime_info.confidence,
            "start_date": regime_info.start_date.isoformat(),
            "duration_days": regime_info.duration_days,
            "indicators": regime_info.indicators
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
