"""
Signal Generation

Generate trading/investment signals from trend and breadth metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class SignalType(Enum):
    """Type of signal."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class TrendSignal:
    """A trading/investment signal."""
    date: datetime
    instrument: str
    signal_type: SignalType
    confidence: float  # 0-1
    reason: str
    metadata: Dict


class SignalGenerator:
    """Generate signals from trend and breadth data."""

    def __init__(
        self,
        strong_uptrend_threshold: float = 0.7,
        strong_downtrend_threshold: float = 0.3,
        breadth_up_threshold: float = 0.6,
        breadth_down_threshold: float = 0.4
    ):
        """
        Initialize signal generator.

        Parameters
        ----------
        strong_uptrend_threshold : float
            Breadth threshold for strong buy signals
        strong_downtrend_threshold : float
            Breadth threshold for strong sell signals
        breadth_up_threshold : float
            Breadth threshold for regular buy signals
        breadth_down_threshold : float
            Breadth threshold for regular sell signals
        """
        self.strong_up_thresh = strong_uptrend_threshold
        self.strong_down_thresh = strong_downtrend_threshold
        self.up_thresh = breadth_up_threshold
        self.down_thresh = breadth_down_threshold

    def generate_breadth_signals(
        self,
        breadth_df: pd.DataFrame,
        asset_class: str
    ) -> List[TrendSignal]:
        """
        Generate signals from breadth metrics.

        Parameters
        ----------
        breadth_df : pd.DataFrame
            Breadth data from compute_group_breadth
        asset_class : str
            Asset class to generate signals for

        Returns
        -------
        signals : list of TrendSignal
        """
        signals = []

        # Filter to asset class
        df = breadth_df[breadth_df['asset_class'] == asset_class].copy()
        df = df.sort_values('date')

        for idx, row in df.iterrows():
            breadth_up = row['breadth_up']
            breadth_down = row['breadth_down']
            avg_score = row.get('avg_trend_score', 0)

            # Determine signal type
            if breadth_up >= self.strong_up_thresh:
                signal_type = SignalType.STRONG_BUY
                confidence = min(breadth_up, 1.0)
                reason = f"Strong uptrend: {breadth_up*100:.1f}% of instruments in uptrend"

            elif breadth_up >= self.up_thresh:
                signal_type = SignalType.BUY
                confidence = breadth_up
                reason = f"Uptrend: {breadth_up*100:.1f}% of instruments in uptrend"

            elif breadth_down >= (1 - self.down_thresh):
                signal_type = SignalType.STRONG_SELL
                confidence = min(breadth_down, 1.0)
                reason = f"Strong downtrend: {breadth_down*100:.1f}% of instruments in downtrend"

            elif breadth_down >= (1 - self.strong_down_thresh):
                signal_type = SignalType.SELL
                confidence = breadth_down
                reason = f"Downtrend: {breadth_down*100:.1f}% of instruments in downtrend"

            else:
                signal_type = SignalType.HOLD
                confidence = 0.5
                reason = "Mixed signals, no clear trend"

            signal = TrendSignal(
                date=row['date'],
                instrument=asset_class,
                signal_type=signal_type,
                confidence=confidence,
                reason=reason,
                metadata={
                    'breadth_up': breadth_up,
                    'breadth_down': breadth_down,
                    'avg_trend_score': avg_score,
                    'num_instruments': row.get('num_instruments', 0)
                }
            )

            signals.append(signal)

        return signals

    def generate_trend_change_signals(
        self,
        breadth_df: pd.DataFrame,
        lookback_window: str = '1m'
    ) -> List[TrendSignal]:
        """
        Generate signals based on breadth changes (momentum).

        Parameters
        ----------
        breadth_df : pd.DataFrame
            Breadth data with change columns
        lookback_window : str
            Which change window to use (e.g., '1m', '3m')

        Returns
        -------
        signals : list of TrendSignal
        """
        signals = []

        change_col = f'breadth_up_change_{lookback_window}'

        if change_col not in breadth_df.columns:
            return signals

        # Get latest data for each asset class
        latest = breadth_df.sort_values('date').groupby('asset_class').tail(1)

        for idx, row in latest.iterrows():
            change = row[change_col]

            if pd.isna(change):
                continue

            asset_class = row['asset_class']

            # Significant positive change
            if change > 0.2:
                signal_type = SignalType.BUY
                confidence = min(abs(change) / 0.5, 1.0)
                reason = f"Strong breadth improvement: +{change*100:.1f}% over {lookback_window}"

            # Significant negative change
            elif change < -0.2:
                signal_type = SignalType.SELL
                confidence = min(abs(change) / 0.5, 1.0)
                reason = f"Strong breadth deterioration: {change*100:.1f}% over {lookback_window}"

            else:
                continue  # No signal for small changes

            signal = TrendSignal(
                date=row['date'],
                instrument=asset_class,
                signal_type=signal_type,
                confidence=confidence,
                reason=reason,
                metadata={
                    'breadth_change': change,
                    'lookback_window': lookback_window,
                    'current_breadth_up': row['breadth_up']
                }
            )

            signals.append(signal)

        return signals

    def generate_factor_signals(
        self,
        factor_trends_df: pd.DataFrame,
        factor_breadth_df: Optional[pd.DataFrame] = None
    ) -> List[TrendSignal]:
        """
        Generate signals for factor tilts.

        Parameters
        ----------
        factor_trends_df : pd.DataFrame
            Factor trend data
        factor_breadth_df : pd.DataFrame, optional
            Factor breadth data

        Returns
        -------
        signals : list of TrendSignal
        """
        signals = []

        # Get latest factor trends
        latest_date = factor_trends_df['date'].max()
        latest = factor_trends_df[factor_trends_df['date'] == latest_date]

        for idx, row in latest.iterrows():
            factor = row['factor']
            trend_state = row['trend_state']
            trend_score = row['trend_score']

            # Strong uptrend in factor = overweight factor
            if trend_state >= 4:
                signal_type = SignalType.STRONG_BUY
                confidence = min(abs(trend_score), 1.0)
                reason = f"Strong uptrend in {factor} factor"

            elif trend_state == 3:
                signal_type = SignalType.BUY
                confidence = min(abs(trend_score) * 0.7, 1.0)
                reason = f"Moderate uptrend in {factor} factor"

            # Strong downtrend = underweight factor
            elif trend_state <= 1:
                signal_type = SignalType.STRONG_SELL
                confidence = min(abs(trend_score), 1.0)
                reason = f"Strong downtrend in {factor} factor"

            elif trend_state == 2:
                signal_type = SignalType.SELL
                confidence = min(abs(trend_score) * 0.7, 1.0)
                reason = f"Moderate downtrend in {factor} factor"

            else:
                signal_type = SignalType.HOLD
                confidence = 0.5
                reason = f"Neutral trend in {factor} factor"

            # Adjust confidence based on breadth if available
            if factor_breadth_df is not None:
                factor_breadth = factor_breadth_df[
                    factor_breadth_df['factor'] == factor
                ]
                if len(factor_breadth) > 0:
                    breadth_spread = factor_breadth['breadth_spread'].iloc[-1]
                    if not pd.isna(breadth_spread):
                        # Higher breadth spread = higher confidence
                        confidence *= (1 + abs(breadth_spread))
                        confidence = min(confidence, 1.0)

            signal = TrendSignal(
                date=latest_date,
                instrument=f"FACTOR_{factor}",
                signal_type=signal_type,
                confidence=confidence,
                reason=reason,
                metadata={
                    'factor': factor,
                    'trend_state': int(trend_state),
                    'trend_score': trend_score,
                    'trend_duration': row.get('trend_duration', 0)
                }
            )

            signals.append(signal)

        return signals

    def generate_divergence_signals(
        self,
        price_df: pd.DataFrame,
        breadth_df: pd.DataFrame,
        asset_class: str
    ) -> List[TrendSignal]:
        """
        Generate signals based on price-breadth divergences.

        Divergence occurs when price makes new highs but breadth deteriorates
        (or vice versa).

        Parameters
        ----------
        price_df : pd.DataFrame
            Price data for instruments in the asset class
        breadth_df : pd.DataFrame
            Breadth data
        asset_class : str
            Asset class to analyze

        Returns
        -------
        signals : list of TrendSignal
        """
        signals = []

        # Filter breadth to asset class
        breadth = breadth_df[breadth_df['asset_class'] == asset_class].copy()
        breadth = breadth.sort_values('date')

        if len(breadth) < 20:
            return signals

        # Get average price for the asset class
        avg_price = price_df.mean(axis=1)

        # Align dates
        common_dates = sorted(set(breadth['date']) & set(avg_price.index))
        if len(common_dates) < 20:
            return signals

        breadth = breadth[breadth['date'].isin(common_dates)]
        avg_price = avg_price[avg_price.index.isin(common_dates)]

        # Check recent divergence (last 20 periods)
        recent_breadth = breadth.tail(20)
        recent_price = avg_price.tail(20)

        # Bearish divergence: price making highs but breadth falling
        if recent_price.iloc[-1] == recent_price.max():
            breadth_slope = (
                recent_breadth['breadth_up'].iloc[-1] -
                recent_breadth['breadth_up'].iloc[0]
            )

            if breadth_slope < -0.1:
                signal = TrendSignal(
                    date=recent_breadth['date'].iloc[-1],
                    instrument=asset_class,
                    signal_type=SignalType.SELL,
                    confidence=min(abs(breadth_slope) / 0.3, 1.0),
                    reason=f"Bearish divergence: Price at highs but breadth falling",
                    metadata={
                        'divergence_type': 'bearish',
                        'breadth_slope': breadth_slope,
                        'price_pct_from_high': 0.0
                    }
                )
                signals.append(signal)

        # Bullish divergence: price making lows but breadth improving
        if recent_price.iloc[-1] == recent_price.min():
            breadth_slope = (
                recent_breadth['breadth_up'].iloc[-1] -
                recent_breadth['breadth_up'].iloc[0]
            )

            if breadth_slope > 0.1:
                signal = TrendSignal(
                    date=recent_breadth['date'].iloc[-1],
                    instrument=asset_class,
                    signal_type=SignalType.BUY,
                    confidence=min(breadth_slope / 0.3, 1.0),
                    reason=f"Bullish divergence: Price at lows but breadth improving",
                    metadata={
                        'divergence_type': 'bullish',
                        'breadth_slope': breadth_slope,
                        'price_pct_from_low': 0.0
                    }
                )
                signals.append(signal)

        return signals

    @staticmethod
    def filter_signals_by_confidence(
        signals: List[TrendSignal],
        min_confidence: float = 0.5
    ) -> List[TrendSignal]:
        """Filter signals by minimum confidence."""
        return [s for s in signals if s.confidence >= min_confidence]

    @staticmethod
    def signals_to_dataframe(signals: List[TrendSignal]) -> pd.DataFrame:
        """Convert signals to DataFrame."""
        if not signals:
            return pd.DataFrame()

        data = []
        for signal in signals:
            row = {
                'date': signal.date,
                'instrument': signal.instrument,
                'signal': signal.signal_type.value,
                'confidence': signal.confidence,
                'reason': signal.reason,
            }
            row.update(signal.metadata)
            data.append(row)

        return pd.DataFrame(data)
