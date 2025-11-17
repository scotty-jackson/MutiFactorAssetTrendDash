"""Advanced Analytics Module."""
from .signals import SignalGenerator, TrendSignal
from .regimes import RegimeDetector, MarketRegime
from .correlations import CorrelationAnalyzer

__all__ = [
    'SignalGenerator',
    'TrendSignal',
    'RegimeDetector',
    'MarketRegime',
    'CorrelationAnalyzer',
]
