"""
Market Regime Detection

Detect and classify market regimes using multiple indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from scipy import stats


class MarketRegime(Enum):
    """Market regime types."""
    BULL_MARKET = "Bull Market"
    BEAR_MARKET = "Bear Market"
    SIDEWAYS = "Sideways"
    HIGH_VOL = "High Volatility"
    LOW_VOL = "Low Volatility"
    RISK_ON = "Risk-On"
    RISK_OFF = "Risk-Off"


@dataclass
class RegimeInfo:
    """Information about current market regime."""
    regime: MarketRegime
    confidence: float
    start_date: datetime
    duration_days: int
    indicators: Dict


class RegimeDetector:
    """Detect market regimes using multiple methods."""

    def __init__(
        self,
        vol_lookback: int = 20,
        trend_lookback: int = 50,
        regime_lookback: int = 252
    ):
        """
        Initialize regime detector.

        Parameters
        ----------
        vol_lookback : int
            Lookback for volatility calculations
        trend_lookback : int
            Lookback for trend detection
        regime_lookback : int
            Lookback for regime percentiles
        """
        self.vol_lookback = vol_lookback
        self.trend_lookback = trend_lookback
        self.regime_lookback = regime_lookback

    def detect_trend_regime(
        self,
        prices: pd.Series,
        current_date: Optional[datetime] = None
    ) -> RegimeInfo:
        """
        Detect bull/bear/sideways regime based on price trends.

        Parameters
        ----------
        prices : pd.Series
            Price series with DatetimeIndex
        current_date : datetime, optional
            Date to detect regime for (default: latest)

        Returns
        -------
        regime_info : RegimeInfo
        """
        if current_date is None:
            current_date = prices.index[-1]

        # Get data up to current date
        prices = prices[prices.index <= current_date]

        if len(prices) < self.trend_lookback:
            return RegimeInfo(
                regime=MarketRegime.SIDEWAYS,
                confidence=0.0,
                start_date=prices.index[0],
                duration_days=len(prices),
                indicators={}
            )

        # Calculate trend indicators
        current_price = prices.iloc[-1]
        sma_50 = prices.tail(self.trend_lookback).mean()
        sma_200 = prices.tail(min(200, len(prices))).mean()

        # Price vs moving averages
        above_50 = current_price > sma_50
        above_200 = current_price > sma_200

        # Slope of linear regression
        x = np.arange(self.trend_lookback)
        y = np.log(prices.tail(self.trend_lookback).values)
        slope, _, r_value, _, _ = stats.linregress(x, y)

        # Annualized slope
        slope_annual = slope * 252

        # Determine regime
        if above_50 and above_200 and slope_annual > 0.1:
            regime = MarketRegime.BULL_MARKET
            confidence = min(slope_annual / 0.3, 1.0)
        elif not above_50 and not above_200 and slope_annual < -0.1:
            regime = MarketRegime.BEAR_MARKET
            confidence = min(abs(slope_annual) / 0.3, 1.0)
        else:
            regime = MarketRegime.SIDEWAYS
            confidence = 1.0 - min(abs(slope_annual) / 0.1, 1.0)

        # Adjust confidence based on R-squared
        confidence *= abs(r_value)

        # Find regime start date
        # Look back to find when regime started
        if regime == MarketRegime.BULL_MARKET:
            # Find when price first crossed above SMA50
            crosses = (prices > sma_50).astype(int).diff()
            last_cross = crosses[crosses == 1].index
            start_date = last_cross[-1] if len(last_cross) > 0 else prices.index[0]
        elif regime == MarketRegime.BEAR_MARKET:
            # Find when price first crossed below SMA50
            crosses = (prices < sma_50).astype(int).diff()
            last_cross = crosses[crosses == 1].index
            start_date = last_cross[-1] if len(last_cross) > 0 else prices.index[0]
        else:
            start_date = current_date

        duration = (current_date - start_date).days

        indicators = {
            'current_price': current_price,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'slope_annual': slope_annual,
            'r_squared': r_value ** 2
        }

        return RegimeInfo(regime, confidence, start_date, duration, indicators)

    def detect_volatility_regime(
        self,
        returns: pd.Series,
        current_date: Optional[datetime] = None
    ) -> RegimeInfo:
        """
        Detect high/low volatility regime.

        Parameters
        ----------
        returns : pd.Series
            Return series
        current_date : datetime, optional
            Date to detect regime for

        Returns
        -------
        regime_info : RegimeInfo
        """
        if current_date is None:
            current_date = returns.index[-1]

        returns = returns[returns.index <= current_date]

        if len(returns) < self.regime_lookback:
            return RegimeInfo(
                regime=MarketRegime.LOW_VOL,
                confidence=0.0,
                start_date=returns.index[0],
                duration_days=len(returns),
                indicators={}
            )

        # Current volatility (annualized)
        current_vol = returns.tail(self.vol_lookback).std() * np.sqrt(252)

        # Historical volatility distribution
        rolling_vol = returns.rolling(self.vol_lookback).std() * np.sqrt(252)
        rolling_vol = rolling_vol.tail(self.regime_lookback)

        # Percentile of current vol
        vol_percentile = (rolling_vol <= current_vol).sum() / len(rolling_vol)

        # High vol if above 75th percentile
        if vol_percentile > 0.75:
            regime = MarketRegime.HIGH_VOL
            confidence = (vol_percentile - 0.75) / 0.25
        # Low vol if below 25th percentile
        elif vol_percentile < 0.25:
            regime = MarketRegime.LOW_VOL
            confidence = (0.25 - vol_percentile) / 0.25
        else:
            # Normal volatility
            regime = MarketRegime.LOW_VOL
            confidence = 0.5

        # Find regime start
        high_vol_threshold = rolling_vol.quantile(0.75)
        low_vol_threshold = rolling_vol.quantile(0.25)

        if regime == MarketRegime.HIGH_VOL:
            regime_mask = rolling_vol > high_vol_threshold
        else:
            regime_mask = rolling_vol < low_vol_threshold

        # Find last regime change
        regime_changes = regime_mask.astype(int).diff()
        last_change = regime_changes[regime_changes != 0].index
        start_date = last_change[-1] if len(last_change) > 0 else returns.index[0]

        duration = (current_date - start_date).days

        indicators = {
            'current_vol': current_vol,
            'vol_percentile': vol_percentile,
            'high_vol_threshold': high_vol_threshold,
            'low_vol_threshold': low_vol_threshold
        }

        return RegimeInfo(regime, confidence, start_date, duration, indicators)

    def detect_risk_regime(
        self,
        equity_returns: pd.Series,
        bond_returns: pd.Series,
        current_date: Optional[datetime] = None
    ) -> RegimeInfo:
        """
        Detect risk-on/risk-off regime based on equity-bond correlation.

        Risk-on: Equities up, bonds down (negative correlation)
        Risk-off: Equities down, bonds up (negative correlation, flight to safety)

        Parameters
        ----------
        equity_returns : pd.Series
            Equity return series
        bond_returns : pd.Series
            Bond return series
        current_date : datetime, optional
            Date to detect regime for

        Returns
        -------
        regime_info : RegimeInfo
        """
        if current_date is None:
            current_date = min(equity_returns.index[-1], bond_returns.index[-1])

        # Align series
        common_dates = sorted(set(equity_returns.index) & set(bond_returns.index))
        common_dates = [d for d in common_dates if d <= current_date]

        if len(common_dates) < self.trend_lookback:
            return RegimeInfo(
                regime=MarketRegime.RISK_OFF,
                confidence=0.0,
                start_date=common_dates[0] if common_dates else current_date,
                duration_days=len(common_dates),
                indicators={}
            )

        eq_ret = equity_returns[equity_returns.index.isin(common_dates)]
        bond_ret = bond_returns[bond_returns.index.isin(common_dates)]

        # Recent equity performance
        recent_eq_ret = eq_ret.tail(self.trend_lookback).sum()

        # Recent bond performance
        recent_bond_ret = bond_ret.tail(self.trend_lookback).sum()

        # Correlation
        correlation = eq_ret.tail(self.trend_lookback).corr(
            bond_ret.tail(self.trend_lookback)
        )

        # Risk-on: equities outperforming, positive sentiment
        if recent_eq_ret > 0.02:
            regime = MarketRegime.RISK_ON
            confidence = min(recent_eq_ret / 0.1, 1.0)
        # Risk-off: equities underperforming, flight to safety
        elif recent_eq_ret < -0.02:
            regime = MarketRegime.RISK_OFF
            confidence = min(abs(recent_eq_ret) / 0.1, 1.0)
        else:
            regime = MarketRegime.RISK_OFF
            confidence = 0.5

        # Adjust based on correlation
        # In risk-off, expect flight to quality (negative corr)
        if regime == MarketRegime.RISK_OFF and correlation < 0:
            confidence *= 1.2
        confidence = min(confidence, 1.0)

        # Find regime start (simplified)
        cumulative_ret = eq_ret.cumsum()
        if recent_eq_ret > 0:
            # Find last trough
            trough_idx = cumulative_ret.tail(self.regime_lookback).idxmin()
            start_date = trough_idx
        else:
            # Find last peak
            peak_idx = cumulative_ret.tail(self.regime_lookback).idxmax()
            start_date = peak_idx

        duration = (current_date - start_date).days

        indicators = {
            'equity_return': recent_eq_ret,
            'bond_return': recent_bond_ret,
            'correlation': correlation
        }

        return RegimeInfo(regime, confidence, start_date, duration, indicators)

    def detect_all_regimes(
        self,
        prices: pd.Series,
        returns: Optional[pd.Series] = None,
        bond_returns: Optional[pd.Series] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, RegimeInfo]:
        """
        Detect all regime types.

        Parameters
        ----------
        prices : pd.Series
            Price series
        returns : pd.Series, optional
            Return series (computed if not provided)
        bond_returns : pd.Series, optional
            Bond returns for risk regime detection
        current_date : datetime, optional
            Date to detect regimes for

        Returns
        -------
        regimes : dict
            Dictionary of regime type to RegimeInfo
        """
        if returns is None:
            returns = prices.pct_change()

        regimes = {}

        # Trend regime
        regimes['trend'] = self.detect_trend_regime(prices, current_date)

        # Volatility regime
        regimes['volatility'] = self.detect_volatility_regime(returns, current_date)

        # Risk regime (if bond data available)
        if bond_returns is not None:
            regimes['risk'] = self.detect_risk_regime(returns, bond_returns, current_date)

        return regimes

    @staticmethod
    def regime_summary(regimes: Dict[str, RegimeInfo]) -> pd.DataFrame:
        """Convert regime info to summary DataFrame."""
        data = []
        for regime_type, info in regimes.items():
            data.append({
                'regime_type': regime_type,
                'regime': info.regime.value,
                'confidence': info.confidence,
                'duration_days': info.duration_days,
                'start_date': info.start_date,
            })

        return pd.DataFrame(data)
