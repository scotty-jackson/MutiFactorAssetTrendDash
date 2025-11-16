"""
Data Loading Utilities

Loaders for CSV files and future API integrations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List
import warnings


class MultiAssetLoader:
    """Load multi-asset price data."""

    def __init__(self, data_dir: str = 'data/raw'):
        self.data_dir = Path(data_dir)

    def load_prices(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load multi-asset prices from CSV.

        Expected format:
        - date column (will be parsed as index)
        - One column per ticker with prices
        OR
        - Long format: date, ticker, close

        Returns
        -------
        prices : pd.DataFrame
            Wide format with DatetimeIndex and ticker columns
        """
        if filepath is None:
            filepath = self.data_dir / 'multi_asset_prices.csv'

        df = pd.read_csv(filepath)

        # Try to detect format
        if 'ticker' in df.columns and 'close' in df.columns:
            # Long format - pivot to wide
            date_col = [c for c in df.columns if 'date' in c.lower()][0]
            df[date_col] = pd.to_datetime(df[date_col])
            prices = df.pivot(index=date_col, columns='ticker', values='close')
        else:
            # Wide format
            date_col = [c for c in df.columns if 'date' in c.lower()]
            if date_col:
                date_col = date_col[0]
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.set_index(date_col)
            prices = df

        prices.index.name = 'date'
        return prices

    def load_metadata(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load instrument metadata.

        Expected columns:
        - ticker
        - asset_class
        - region
        - sector
        - (other grouping columns)
        """
        if filepath is None:
            filepath = self.data_dir / 'multi_asset_metadata.csv'

        metadata = pd.read_csv(filepath)
        return metadata


class FactorDataLoader:
    """Load factor return data."""

    def __init__(self, data_dir: str = 'data/raw'):
        self.data_dir = Path(data_dir)

    def load_factor_returns(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load factor returns (Fama-French style).

        Expected format:
        - Date column
        - Factor columns (HML, SMB, MOM, etc.)
        - Returns can be in decimal or percentage form
        """
        if filepath is None:
            filepath = self.data_dir / 'factor_returns.csv'

        df = pd.read_csv(filepath)

        # Parse date
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        if date_cols:
            date_col = date_cols[0]
        else:
            date_col = df.columns[0]

        # Try different date formats
        for fmt in ['%Y%m%d', '%Y-%m-%d', None]:
            try:
                df[date_col] = pd.to_datetime(df[date_col], format=fmt)
                break
            except:
                continue

        df = df.set_index(date_col)
        df.index.name = 'date'

        # Remove RF column if present
        if 'RF' in df.columns:
            df = df.drop(columns=['RF'])

        return df

    def load_market_returns(self, filepath: Optional[str] = None) -> pd.Series:
        """Load market return series."""
        if filepath is None:
            filepath = self.data_dir / 'market_returns.csv'

        df = pd.read_csv(filepath)

        date_col = [c for c in df.columns if 'date' in c.lower()][0]
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

        # Return first non-date column as series
        return_col = [c for c in df.columns if c != date_col][0]
        return df[return_col]


class StockDataLoader:
    """Load stock-level data."""

    def __init__(self, data_dir: str = 'data/raw'):
        self.data_dir = Path(data_dir)

    def load_stock_prices(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """Load stock prices."""
        if filepath is None:
            filepath = self.data_dir / 'stock_prices.csv'

        df = pd.read_csv(filepath)

        # Long or wide format
        if 'ticker' in df.columns or 'permno' in df.columns:
            # Long format
            id_col = 'ticker' if 'ticker' in df.columns else 'permno'
            date_col = [c for c in df.columns if 'date' in c.lower()][0]
            df[date_col] = pd.to_datetime(df[date_col])

            prices = df.pivot(index=date_col, columns=id_col, values='close')
        else:
            # Wide format
            date_col = [c for c in df.columns if 'date' in c.lower()][0]
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
            prices = df

        prices.index.name = 'date'
        return prices

    def load_factor_scores(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load factor scores for stocks.

        Expected format:
        - date, ticker/permno, value_score, momentum_score, quality_score, etc.
        """
        if filepath is None:
            filepath = self.data_dir / 'factor_scores.csv'

        df = pd.read_csv(filepath)

        date_col = [c for c in df.columns if 'date' in c.lower()][0]
        df[date_col] = pd.to_datetime(df[date_col])

        return df

    def load_fundamentals(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load fundamental data.

        Expected format:
        - date, ticker/permno, pb, pe, ev_ebitda, etc.
        """
        if filepath is None:
            filepath = self.data_dir / 'fundamentals.csv'

        df = pd.read_csv(filepath)

        date_col = [c for c in df.columns if 'date' in c.lower()][0]
        df[date_col] = pd.to_datetime(df[date_col])

        return df


def generate_sample_data(output_dir: str = 'data/raw'):
    """
    Generate sample data for testing and demonstration.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate multi-asset prices
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    np.random.seed(42)

    multi_asset_prices = pd.DataFrame({
        'SPY': 100 * (1.0002 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.01),
        'QQQ': 100 * (1.0003 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.015),
        'IWM': 100 * (1.0001 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.012),
        'TLT': 100 * (0.9998 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.008),
        'GLD': 100 * (1.0001 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.01),
        'USO': 100 * (1.0002 ** np.arange(len(dates))) * (1 + np.random.randn(len(dates)) * 0.02),
    }, index=dates)
    multi_asset_prices.index.name = 'date'
    multi_asset_prices.to_csv(output_path / 'multi_asset_prices.csv')

    # Generate metadata
    metadata = pd.DataFrame({
        'ticker': ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'USO'],
        'asset_class': ['Equity', 'Equity', 'Equity', 'Bond', 'Commodity', 'Commodity'],
        'region': ['US', 'US', 'US', 'US', 'Global', 'Global'],
        'sector': ['Broad', 'Tech', 'SmallCap', 'LongTerm', 'Gold', 'Energy'],
    })
    metadata.to_csv(output_path / 'multi_asset_metadata.csv', index=False)

    # Generate factor returns
    factor_returns = pd.DataFrame({
        'date': dates,
        'HML': np.random.randn(len(dates)) * 0.5 + 0.02,
        'SMB': np.random.randn(len(dates)) * 0.4 + 0.01,
        'MOM': np.random.randn(len(dates)) * 0.6 + 0.03,
    })
    factor_returns.to_csv(output_path / 'factor_returns.csv', index=False)

    print(f"Sample data generated in {output_path}")
    return output_path
