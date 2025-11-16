# Multi Asset Factor Trend Dashboard - Architecture

## Overview

This system provides a comprehensive dashboard for analyzing trends across multiple asset classes and equity factors, with drill-down capabilities for detailed analysis.

## Directory Structure

```
MutiFactorAssetTrendDash/
├── src/
│   ├── trend_engine/          # Core trend analysis engine
│   │   ├── __init__.py
│   │   ├── trend_engine.py    # Moving averages, trend scores, state classification
│   │   └── duration.py        # Trend duration calculations
│   ├── analysis/              # Analysis modules
│   │   ├── __init__.py
│   │   ├── multi_asset_breadth.py   # Cross-asset breadth metrics
│   │   ├── factor_trends.py         # Factor index trend analysis
│   │   ├── factor_breadth.py        # Within-factor breadth at stock level
│   │   └── valuation_spreads.py     # Factor valuation spread analysis
│   ├── data/                  # Data loading and management
│   │   ├── __init__.py
│   │   ├── loaders.py         # CSV and API data loaders
│   │   └── schemas.py         # Data schema definitions
│   ├── config/                # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration classes and defaults
│   │   └── universes.py       # Universe definitions
│   ├── backend/               # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app
│   │   ├── api/               # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── asset_breadth.py
│   │   │   ├── factor_trends.py
│   │   │   ├── factor_breadth.py
│   │   │   └── valuation.py
│   │   └── compute.py         # Batch computation logic
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       └── helpers.py
├── frontend/                  # React frontend
│   ├── package.json
│   ├── public/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Dashboard pages
│   │   ├── api/               # API client
│   │   └── App.js
│   └── ...
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_trend_engine.py
│   ├── test_multi_asset_breadth.py
│   ├── test_factor_trends.py
│   ├── test_factor_breadth.py
│   └── test_valuation_spreads.py
├── data/                      # Data directory (git-ignored)
│   ├── raw/                   # Raw CSV files
│   ├── processed/             # Processed parquet files
│   └── cache/                 # Cached computations
├── config/                    # Configuration files
│   ├── default_config.yaml
│   └── universes.yaml
├── notebooks/                 # Analysis notebooks
├── scripts/                   # Utility scripts
│   ├── compute_batch.py       # Batch computation script
│   └── download_sample_data.py
├── requirements.txt
├── setup.py
└── README.md
```

## Data Flow

1. **Data Ingestion**: CSV files or API calls → Data Loaders
2. **Trend Computation**: Raw prices → Trend Engine → Trend scores, states, durations
3. **Aggregation**: Individual trends → Analysis modules → Breadth metrics, spreads
4. **Storage**: Computed metrics → Parquet files (for performance)
5. **API**: FastAPI serves computed metrics via REST endpoints
6. **Frontend**: React app fetches and visualizes data

## Key Design Principles

1. **Data-Driven**: All parameters, universes, and thresholds are configurable
2. **Modular**: Each module has a single, clear responsibility
3. **Efficient**: Panel operations with MultiIndex DataFrames
4. **Extensible**: Easy to add new assets, factors, or metrics
5. **Production-Ready**: Proper error handling, logging, and testing

## Computation Modes

### Precompute Mode (Recommended for Production)
- Batch script runs all computations
- Results saved to Parquet files
- API serves cached results (fast)
- Schedule with cron/airflow

### On-Demand Mode (For Development)
- API computes metrics on each request
- Good for small datasets or testing
- Higher latency

## Module Details

### Trend Engine
- **Input**: Price series (pd.Series or pd.DataFrame)
- **Output**: Trend scores, discrete states, durations
- **Configurable**: MA windows, slope window, weights, thresholds

### Multi Asset Breadth
- **Input**: Multi-asset price panel, metadata
- **Output**: Breadth metrics by group (asset_class, region, sector)
- **Metrics**: %Up, %Down, avg trend score, median duration, changes

### Factor Trends
- **Input**: Factor return series (Fama-French format)
- **Output**: Factor index trends, states, durations, excess returns
- **Extensible**: Easy to add new factors

### Factor Breadth
- **Input**: Stock prices, factor scores
- **Output**: Breadth within factor buckets (e.g., high value vs low value)
- **Metrics**: Breadth spreads, trend distributions

### Valuation Spreads
- **Input**: Fundamental data (P/B, P/E, EV/EBITDA), factor buckets
- **Output**: Valuation spreads, z-scores, percentiles
- **Historical normalization**: Tracks if factors are cheap/rich vs history
