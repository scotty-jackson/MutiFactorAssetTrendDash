"""
Configuration Management

Central configuration for all analysis parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import yaml
from pathlib import Path


@dataclass
class TrendEngineConfig:
    """Configuration for trend analysis."""
    short_window: int = 50
    long_window: int = 200
    slope_window: int = 252
    weight_short_ma: float = 0.4
    weight_long_ma: float = 0.4
    weight_slope: float = 0.2


@dataclass
class BreadthConfig:
    """Configuration for breadth analysis."""
    min_instruments_per_group: int = 3
    lookback_windows: Dict[str, int] = field(default_factory=lambda: {
        '1m': 21,
        '3m': 63,
        '6m': 126,
        '12m': 252,
    })


@dataclass
class FactorConfig:
    """Configuration for factor analysis."""
    excess_return_windows: List[int] = field(default_factory=lambda: [63, 126, 252])
    top_quantile: float = 0.1
    bottom_quantile: float = 0.1
    rebalance_freq: str = 'M'  # Monthly


@dataclass
class DataConfig:
    """Configuration for data paths and sources."""
    data_dir: str = 'data'
    raw_data_dir: str = 'data/raw'
    processed_data_dir: str = 'data/processed'
    cache_dir: str = 'data/cache'


@dataclass
class DashboardConfig:
    """Main dashboard configuration."""
    trend_engine: TrendEngineConfig = field(default_factory=TrendEngineConfig)
    breadth: BreadthConfig = field(default_factory=BreadthConfig)
    factor: FactorConfig = field(default_factory=FactorConfig)
    data: DataConfig = field(default_factory=DataConfig)

    @classmethod
    def from_yaml(cls, filepath: str) -> 'DashboardConfig':
        """Load configuration from YAML file."""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)

        return cls(
            trend_engine=TrendEngineConfig(**config_dict.get('trend_engine', {})),
            breadth=BreadthConfig(**config_dict.get('breadth', {})),
            factor=FactorConfig(**config_dict.get('factor', {})),
            data=DataConfig(**config_dict.get('data', {})),
        )

    def to_yaml(self, filepath: str):
        """Save configuration to YAML file."""
        config_dict = {
            'trend_engine': self.trend_engine.__dict__,
            'breadth': self.breadth.__dict__,
            'factor': self.factor.__dict__,
            'data': self.data.__dict__,
        }

        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


# Default configuration
DEFAULT_CONFIG = DashboardConfig()
