"""
Data Validation Utilities

Validate input data quality and schema compliance.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict


class DataValidator:
    """Validate financial data quality."""

    @staticmethod
    def validate_price_data(
        df: pd.DataFrame,
        min_price: float = 0.01,
        max_missing_pct: float = 0.1,
        check_monotonic_index: bool = True
    ) -> ValidationResult:
        """
        Validate price data.

        Parameters
        ----------
        df : pd.DataFrame
            Price data with DatetimeIndex
        min_price : float
            Minimum valid price
        max_missing_pct : float
            Maximum allowed missing data percentage
        check_monotonic_index : bool
            Check if index is monotonically increasing

        Returns
        -------
        result : ValidationResult
        """
        errors = []
        warnings = []
        stats = {}

        # Check index
        if not isinstance(df.index, pd.DatetimeIndex):
            errors.append("Index must be DatetimeIndex")

        if check_monotonic_index and not df.index.is_monotonic_increasing:
            errors.append("Index must be monotonically increasing")

        # Check for duplicates
        if df.index.duplicated().any():
            dup_dates = df.index[df.index.duplicated()].unique()
            errors.append(f"Duplicate dates found: {len(dup_dates)} dates")

        # Check price values
        if (df < 0).any().any():
            neg_cols = df.columns[(df < 0).any()].tolist()
            errors.append(f"Negative prices found in: {neg_cols}")

        if (df < min_price).any().any():
            low_cols = df.columns[(df < min_price).any()].tolist()
            warnings.append(f"Prices below {min_price} in: {low_cols}")

        # Check for missing data
        missing_pct = df.isnull().sum() / len(df)
        high_missing = missing_pct[missing_pct > max_missing_pct]

        if len(high_missing) > 0:
            warnings.append(
                f"{len(high_missing)} columns have >{max_missing_pct*100}% missing data"
            )

        # Check for flat prices (possible data issue)
        for col in df.columns:
            if df[col].nunique() == 1:
                warnings.append(f"Column {col} has constant price (possible data issue)")

        # Check for extreme returns
        returns = df.pct_change()
        extreme_returns = (returns.abs() > 0.5).sum()
        if extreme_returns.any():
            warnings.append(
                f"Extreme returns (>50%) found in {extreme_returns[extreme_returns > 0].to_dict()}"
            )

        # Compute stats
        stats = {
            'num_instruments': len(df.columns),
            'num_periods': len(df),
            'date_range': (df.index.min(), df.index.max()),
            'missing_pct': missing_pct.to_dict(),
            'avg_price': df.mean().to_dict(),
        }

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, errors, warnings, stats)

    @staticmethod
    def validate_returns(
        returns: pd.DataFrame,
        max_return: float = 1.0,
        check_autocorrelation: bool = True
    ) -> ValidationResult:
        """
        Validate return data.

        Parameters
        ----------
        returns : pd.DataFrame
            Return series
        max_return : float
            Maximum expected absolute return
        check_autocorrelation : bool
            Check for suspicious autocorrelation

        Returns
        -------
        result : ValidationResult
        """
        errors = []
        warnings = []
        stats = {}

        # Check for extreme values
        extreme = (returns.abs() > max_return).sum()
        if extreme.any():
            warnings.append(
                f"Extreme returns (>{max_return}) found: {extreme[extreme > 0].to_dict()}"
            )

        # Check for all zeros (suspicious)
        for col in returns.columns:
            if (returns[col] == 0).sum() / len(returns) > 0.5:
                warnings.append(f"Column {col} has >50% zero returns")

        # Check autocorrelation
        if check_autocorrelation:
            for col in returns.columns[:5]:  # Check first 5 for performance
                autocorr = returns[col].autocorr(lag=1)
                if abs(autocorr) > 0.5:
                    warnings.append(f"High autocorrelation ({autocorr:.2f}) in {col}")

        stats = {
            'mean_return': returns.mean().to_dict(),
            'volatility': returns.std().to_dict(),
            'sharpe': (returns.mean() / returns.std()).to_dict(),
        }

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, errors, warnings, stats)

    @staticmethod
    def validate_metadata(
        metadata: pd.DataFrame,
        required_columns: List[str] = None
    ) -> ValidationResult:
        """
        Validate metadata structure.

        Parameters
        ----------
        metadata : pd.DataFrame
            Metadata DataFrame
        required_columns : list of str
            Required columns

        Returns
        -------
        result : ValidationResult
        """
        errors = []
        warnings = []
        stats = {}

        if required_columns is None:
            required_columns = ['ticker', 'asset_class']

        # Check required columns
        missing_cols = set(required_columns) - set(metadata.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

        # Check for duplicates
        if 'ticker' in metadata.columns:
            dup_tickers = metadata['ticker'].duplicated()
            if dup_tickers.any():
                errors.append(f"Duplicate tickers: {metadata.loc[dup_tickers, 'ticker'].tolist()}")

        # Check for missing values in key columns
        for col in required_columns:
            if col in metadata.columns:
                missing = metadata[col].isnull().sum()
                if missing > 0:
                    warnings.append(f"{missing} missing values in {col}")

        stats = {
            'num_instruments': len(metadata),
            'columns': list(metadata.columns),
        }

        if 'asset_class' in metadata.columns:
            stats['asset_class_counts'] = metadata['asset_class'].value_counts().to_dict()

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, errors, warnings, stats)

    @staticmethod
    def check_data_freshness(
        df: pd.DataFrame,
        max_age_days: int = 7
    ) -> Tuple[bool, str]:
        """
        Check if data is fresh (recently updated).

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with DatetimeIndex
        max_age_days : int
            Maximum acceptable age in days

        Returns
        -------
        is_fresh : bool
        message : str
        """
        latest_date = df.index.max()
        age = (datetime.now() - latest_date).days

        if age > max_age_days:
            return False, f"Data is {age} days old (max: {max_age_days})"

        return True, f"Data is fresh ({age} days old)"


def validate_pipeline_inputs(
    prices: pd.DataFrame,
    metadata: pd.DataFrame,
    min_instruments: int = 5
) -> Dict[str, ValidationResult]:
    """
    Validate all inputs for the analysis pipeline.

    Parameters
    ----------
    prices : pd.DataFrame
        Price data
    metadata : pd.DataFrame
        Instrument metadata
    min_instruments : int
        Minimum required instruments

    Returns
    -------
    results : dict
        Validation results for each component
    """
    validator = DataValidator()

    results = {
        'prices': validator.validate_price_data(prices),
        'metadata': validator.validate_metadata(metadata),
    }

    # Check alignment
    if 'ticker' in metadata.columns:
        common = set(prices.columns) & set(metadata['ticker'])
        if len(common) < min_instruments:
            results['alignment'] = ValidationResult(
                is_valid=False,
                errors=[f"Only {len(common)} instruments in both prices and metadata (min: {min_instruments})"],
                warnings=[],
                stats={'common_instruments': len(common)}
            )
        else:
            results['alignment'] = ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                stats={'common_instruments': len(common)}
            )

    return results
