"""
Signals API Endpoints

Serve trading/investment signals.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analytics.signals import SignalGenerator, SignalType
from config import DEFAULT_CONFIG

router = APIRouter(prefix="/api/signals", tags=["signals"])

CACHE_DIR = Path(DEFAULT_CONFIG.data.cache_dir)


@router.get("/breadth")
def get_breadth_signals(
    asset_class: Optional[str] = None,
    min_confidence: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Get signals based on breadth metrics.

    Parameters:
    - asset_class: Filter by asset class
    - min_confidence: Minimum signal confidence (0-1)
    """
    try:
        # Load breadth data
        breadth_file = CACHE_DIR / "asset_breadth_full.parquet"

        if not breadth_file.exists():
            raise HTTPException(status_code=404, detail="Breadth data not found")

        breadth_df = pd.read_parquet(breadth_file)

        # Generate signals
        generator = SignalGenerator()

        if asset_class:
            signals = generator.generate_breadth_signals(breadth_df, asset_class)
        else:
            # Generate for all asset classes
            signals = []
            for ac in breadth_df['asset_class'].unique():
                signals.extend(generator.generate_breadth_signals(breadth_df, ac))

        # Filter by confidence
        signals = generator.filter_signals_by_confidence(signals, min_confidence)

        # Convert to DataFrame then to dict
        signals_df = generator.signals_to_dataframe(signals)

        if len(signals_df) == 0:
            return {"data": [], "count": 0}

        # Get most recent signal for each instrument
        latest_signals = signals_df.sort_values('date').groupby('instrument').tail(1)

        return {
            "data": latest_signals.to_dict(orient="records"),
            "count": len(latest_signals),
            "columns": list(latest_signals.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum")
def get_momentum_signals(
    lookback_window: str = Query(default="1m", regex="^(1m|3m|6m|12m)$"),
    min_confidence: float = Query(default=0.6, ge=0.0, le=1.0)
):
    """
    Get signals based on breadth momentum (changes).

    Parameters:
    - lookback_window: Time window for momentum (1m, 3m, 6m, 12m)
    - min_confidence: Minimum signal confidence
    """
    try:
        breadth_file = CACHE_DIR / "asset_breadth_full.parquet"

        if not breadth_file.exists():
            raise HTTPException(status_code=404, detail="Breadth data not found")

        breadth_df = pd.read_parquet(breadth_file)

        # Generate momentum signals
        generator = SignalGenerator()
        signals = generator.generate_trend_change_signals(breadth_df, lookback_window)

        # Filter by confidence
        signals = generator.filter_signals_by_confidence(signals, min_confidence)

        signals_df = generator.signals_to_dataframe(signals)

        if len(signals_df) == 0:
            return {"data": [], "count": 0}

        return {
            "data": signals_df.to_dict(orient="records"),
            "count": len(signals_df),
            "columns": list(signals_df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors")
def get_factor_signals(
    min_confidence: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Get factor tilt signals.

    Parameters:
    - min_confidence: Minimum signal confidence
    """
    try:
        trends_file = CACHE_DIR / "factor_trends_full.parquet"

        if not trends_file.exists():
            raise HTTPException(status_code=404, detail="Factor trends not found")

        trends_df = pd.read_parquet(trends_file)

        # Try to load factor breadth if available
        breadth_file = CACHE_DIR / "factor_breadth_latest.parquet"
        breadth_df = None
        if breadth_file.exists():
            breadth_df = pd.read_parquet(breadth_file)

        # Generate factor signals
        generator = SignalGenerator()
        signals = generator.generate_factor_signals(trends_df, breadth_df)

        # Filter by confidence
        signals = generator.filter_signals_by_confidence(signals, min_confidence)

        signals_df = generator.signals_to_dataframe(signals)

        if len(signals_df) == 0:
            return {"data": [], "count": 0}

        return {
            "data": signals_df.to_dict(orient="records"),
            "count": len(signals_df),
            "columns": list(signals_df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
def get_all_signals(
    min_confidence: float = Query(default=0.5, ge=0.0, le=1.0)
):
    """
    Get all types of signals.

    Parameters:
    - min_confidence: Minimum signal confidence
    """
    try:
        all_signals = []

        # Breadth signals
        try:
            breadth_response = get_breadth_signals(min_confidence=min_confidence)
            if breadth_response["count"] > 0:
                for signal in breadth_response["data"]:
                    signal['signal_type'] = 'breadth'
                    all_signals.append(signal)
        except:
            pass

        # Momentum signals
        try:
            momentum_response = get_momentum_signals(min_confidence=min_confidence)
            if momentum_response["count"] > 0:
                for signal in momentum_response["data"]:
                    signal['signal_type'] = 'momentum'
                    all_signals.append(signal)
        except:
            pass

        # Factor signals
        try:
            factor_response = get_factor_signals(min_confidence=min_confidence)
            if factor_response["count"] > 0:
                for signal in factor_response["data"]:
                    signal['signal_type'] = 'factor'
                    all_signals.append(signal)
        except:
            pass

        return {
            "data": all_signals,
            "count": len(all_signals),
            "signal_types": list(set(s['signal_type'] for s in all_signals))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
def get_signals_summary():
    """Get summary of current signals by type and direction."""
    try:
        all_signals_response = get_all_signals(min_confidence=0.3)

        if all_signals_response["count"] == 0:
            return {"summary": {}, "total_signals": 0}

        signals_df = pd.DataFrame(all_signals_response["data"])

        summary = {}

        # Group by signal type and signal
        for signal_type in signals_df['signal_type'].unique():
            type_df = signals_df[signals_df['signal_type'] == signal_type]

            summary[signal_type] = {
                'total': len(type_df),
                'by_direction': type_df['signal'].value_counts().to_dict(),
                'avg_confidence': type_df['confidence'].mean()
            }

        return {
            "summary": summary,
            "total_signals": len(signals_df),
            "strong_buy": len(signals_df[signals_df['signal'] == SignalType.STRONG_BUY.value]),
            "buy": len(signals_df[signals_df['signal'] == SignalType.BUY.value]),
            "hold": len(signals_df[signals_df['signal'] == SignalType.HOLD.value]),
            "sell": len(signals_df[signals_df['signal'] == SignalType.SELL.value]),
            "strong_sell": len(signals_df[signals_df['signal'] == SignalType.STRONG_SELL.value]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
