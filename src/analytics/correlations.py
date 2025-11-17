"""
Correlation Analysis

Advanced correlation and co-movement analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform


class CorrelationAnalyzer:
    """Analyze correlations and co-movements."""

    @staticmethod
    def compute_rolling_correlation(
        df: pd.DataFrame,
        window: int = 60,
        min_periods: Optional[int] = None
    ) -> Dict[Tuple[str, str], pd.Series]:
        """
        Compute rolling pairwise correlations.

        Parameters
        ----------
        df : pd.DataFrame
            Data with columns to correlate
        window : int
            Rolling window
        min_periods : int, optional
            Minimum periods required

        Returns
        -------
        correlations : dict
            Dictionary mapping (col1, col2) to correlation series
        """
        if min_periods is None:
            min_periods = window // 2

        correlations = {}

        for i, col1 in enumerate(df.columns):
            for col2 in df.columns[i+1:]:
                corr = df[col1].rolling(window, min_periods=min_periods).corr(
                    df[col2]
                )
                correlations[(col1, col2)] = corr

        return correlations

    @staticmethod
    def detect_correlation_regimes(
        corr_series: pd.Series,
        high_threshold: float = 0.7,
        low_threshold: float = 0.3
    ) -> pd.Series:
        """
        Classify correlation into regimes (high/medium/low).

        Parameters
        ----------
        corr_series : pd.Series
            Correlation time series
        high_threshold : float
            Threshold for high correlation
        low_threshold : float
            Threshold for low correlation

        Returns
        -------
        regimes : pd.Series
            Regime labels
        """
        regimes = pd.Series('Medium', index=corr_series.index)
        regimes[corr_series.abs() >= high_threshold] = 'High'
        regimes[corr_series.abs() <= low_threshold] = 'Low'

        return regimes

    @staticmethod
    def compute_hierarchical_clusters(
        corr_matrix: pd.DataFrame,
        method: str = 'ward'
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Compute hierarchical clustering from correlation matrix.

        Parameters
        ----------
        corr_matrix : pd.DataFrame
            Correlation matrix
        method : str
            Clustering method ('ward', 'average', 'complete')

        Returns
        -------
        linkage : np.ndarray
            Hierarchical clustering linkage
        labels : list
            Column labels (ordered by clustering)
        """
        # Convert correlation to distance
        distance = 1 - corr_matrix.abs()

        # Ensure it's a proper distance matrix
        distance = distance.fillna(1)
        np.fill_diagonal(distance.values, 0)

        # Compute linkage
        linkage = hierarchy.linkage(squareform(distance), method=method)

        # Get dendrogram order
        dendro = hierarchy.dendrogram(linkage, no_plot=True)
        ordered_indices = dendro['leaves']
        labels = [corr_matrix.columns[i] for i in ordered_indices]

        return linkage, labels

    @staticmethod
    def compute_diversification_ratio(
        returns: pd.DataFrame,
        weights: Optional[np.ndarray] = None
    ) -> float:
        """
        Compute diversification ratio.

        DR = (weighted avg of volatilities) / (portfolio volatility)
        Higher DR = more diversification benefit

        Parameters
        ----------
        returns : pd.DataFrame
            Return series for each asset
        weights : np.ndarray, optional
            Portfolio weights (equal weight if None)

        Returns
        -------
        diversification_ratio : float
        """
        if weights is None:
            weights = np.ones(len(returns.columns)) / len(returns.columns)

        # Individual volatilities
        vols = returns.std()

        # Weighted average volatility
        weighted_avg_vol = (weights * vols).sum()

        # Portfolio volatility
        cov_matrix = returns.cov()
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)

        if portfolio_vol == 0:
            return 1.0

        return weighted_avg_vol / portfolio_vol

    @staticmethod
    def compute_correlation_stability(
        df: pd.DataFrame,
        window: int = 252,
        step: int = 63
    ) -> pd.DataFrame:
        """
        Measure stability of correlations over time.

        Parameters
        ----------
        df : pd.DataFrame
            Return data
        window : int
            Window for correlation calculation
        step : int
            Step size for rolling windows

        Returns
        -------
        stability : pd.DataFrame
            Correlation stability metrics
        """
        results = []

        # Compute correlations over rolling windows
        for start in range(0, len(df) - window, step):
            end = start + window
            window_data = df.iloc[start:end]

            corr_matrix = window_data.corr()

            # Average correlation
            avg_corr = corr_matrix.values[np.triu_indices_from(
                corr_matrix.values, k=1
            )].mean()

            results.append({
                'date': df.index[end-1],
                'avg_correlation': avg_corr,
                'max_correlation': corr_matrix.values[np.triu_indices_from(
                    corr_matrix.values, k=1
                )].max(),
                'min_correlation': corr_matrix.values[np.triu_indices_from(
                    corr_matrix.values, k=1
                )].min(),
            })

        stability_df = pd.DataFrame(results)

        # Compute stability metrics
        if len(stability_df) > 1:
            stability_df['correlation_volatility'] = stability_df['avg_correlation'].rolling(4).std()

        return stability_df

    @staticmethod
    def identify_correlation_breakpoints(
        corr_series: pd.Series,
        threshold_change: float = 0.3
    ) -> pd.DataFrame:
        """
        Identify significant changes in correlation (breakpoints).

        Parameters
        ----------
        corr_series : pd.Series
            Time series of correlation
        threshold_change : float
            Minimum change to be considered a breakpoint

        Returns
        -------
        breakpoints : pd.DataFrame
            DataFrame with breakpoint dates and changes
        """
        # Compute changes
        changes = corr_series.diff().abs()

        # Identify significant changes
        breakpoints_mask = changes >= threshold_change

        breakpoint_dates = corr_series[breakpoints_mask].index
        breakpoint_values = corr_series[breakpoints_mask].values
        change_magnitudes = changes[breakpoints_mask].values

        breakpoints_df = pd.DataFrame({
            'date': breakpoint_dates,
            'correlation': breakpoint_values,
            'change_magnitude': change_magnitudes
        })

        return breakpoints_df
