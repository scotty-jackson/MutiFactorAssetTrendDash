# Multi Asset Factor Trend Dashboard

A production-ready system for analyzing trends across multiple asset classes and equity factors, with comprehensive breadth metrics and valuation spreads.

## Features

- **Trend Engine**: Robust trend analysis using moving averages, slopes, and composite scoring
- **Multi-Asset Breadth**: Track trend breadth across asset classes, regions, and sectors
- **Factor Trends**: Analyze Fama-French style factor indices with regime detection
- **Factor Breadth**: Within-factor breadth analysis (e.g., high vs low value stocks)
- **Valuation Spreads**: Track factor valuation spreads with historical normalization
- **REST API**: FastAPI backend serving precomputed metrics
- **Configurable**: Data-driven design with YAML configuration
- **Extensible**: Modular architecture for easy additions

## Project Structure

```
MutiFactorAssetTrendDash/
├── src/
│   ├── trend_engine/         # Core trend analysis
│   ├── analysis/             # Breadth, factor, and valuation modules
│   ├── data/                 # Data loaders
│   ├── config/               # Configuration management
│   └── backend/              # FastAPI server
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── data/                     # Data directory (gitignored)
│   ├── raw/                  # Raw CSV files
│   ├── processed/            # Processed data
│   └── cache/                # Cached computations
├── requirements.txt
├── setup.py
└── README.md
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
cd MutiFactorAssetTrendDash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"
```

### 2. Generate Sample Data

```bash
# Generate sample data for demonstration
python -c "from src.data.loaders import generate_sample_data; generate_sample_data()"
```

This creates:
- `data/raw/multi_asset_prices.csv` - Sample ETF prices
- `data/raw/multi_asset_metadata.csv` - Asset classification metadata
- `data/raw/factor_returns.csv` - Sample Fama-French factor returns

### 3. Run Batch Computation

```bash
# Compute all metrics and cache results
python scripts/compute_batch.py
```

This will:
- Load price and factor data
- Compute trend metrics for all instruments and factors
- Calculate breadth statistics
- Save results to `data/cache/` for fast API serving

### 4. Start the API Server

```bash
# Option 1: Direct Python
cd src/backend
python main.py

# Option 2: With uvicorn (recommended for development)
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`

Interactive docs at: `http://localhost:8000/docs`

### 5. Query the API

```bash
# Get current asset breadth
curl http://localhost:8000/api/asset-breadth/current

# Get historical breadth for Equity
curl "http://localhost:8000/api/asset-breadth/history?asset_class=Equity&limit=100"

# Get current factor trends
curl http://localhost:8000/api/factor-trends/current

# Get historical trends for a specific factor
curl "http://localhost:8000/api/factor-trends/history?factor=HML&limit=252"
```

## Usage Guide

### Preparing Your Own Data

#### Multi-Asset Prices

Create `data/raw/multi_asset_prices.csv`:

```csv
date,SPY,TLT,GLD,USO
2020-01-01,300.5,140.2,150.3,60.5
2020-01-02,301.2,140.5,149.8,61.0
...
```

Create `data/raw/multi_asset_metadata.csv`:

```csv
ticker,asset_class,region,sector
SPY,Equity,US,Broad
TLT,Bond,US,LongTerm
GLD,Commodity,Global,Precious
USO,Commodity,Global,Energy
```

#### Factor Returns

Create `data/raw/factor_returns.csv`:

```csv
date,HML,SMB,MOM,RMW,CMA
20200101,0.15,0.08,-0.12,0.05,0.03
20200102,-0.08,0.12,0.18,-0.02,0.01
...
```

Format:
- Returns can be in decimal (0.01 = 1%) or percentage (1.0 = 1%) form
- Date format: YYYYMMDD or YYYY-MM-DD

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_trend_engine.py -v

# Run specific test class
pytest tests/test_multi_asset_breadth.py::TestComputeGroupBreadth -v
```

### Configuration

Edit `config/default_config.yaml` (create if doesn't exist):

```yaml
trend_engine:
  short_window: 50
  long_window: 200
  slope_window: 252
  weight_short_ma: 0.4
  weight_long_ma: 0.4
  weight_slope: 0.2

breadth:
  min_instruments_per_group: 3
  lookback_windows:
    1m: 21
    3m: 63
    6m: 126
    12m: 252

factor:
  excess_return_windows: [63, 126, 252]
  top_quantile: 0.1
  bottom_quantile: 0.1
  rebalance_freq: M

data:
  data_dir: data
  raw_data_dir: data/raw
  processed_data_dir: data/processed
  cache_dir: data/cache
```

## Module Documentation

### Trend Engine

The core trend analysis engine computes:
- **Trend Score**: Weighted combination of price vs MA distances and slope
- **Trend State**: Discrete classification (Strong Down/Moderate Down/Neutral/Moderate Up/Strong Up)
- **Trend Duration**: Number of consecutive periods in current state

```python
from src.trend_engine.trend_engine import TrendConfig, compute_all_trend_metrics
import pandas as pd

# Load price data
prices = pd.read_csv('prices.csv', index_col='date', parse_dates=True)

# Configure and compute
config = TrendConfig(short_window=50, long_window=200)
metrics = compute_all_trend_metrics(prices, config)

# Access results
trend_scores = metrics['trend_scores']
trend_states = metrics['trend_states']
trend_durations = metrics['trend_durations']
```

### Multi-Asset Breadth

Compute breadth metrics across asset groups:

```python
from src.analysis.multi_asset_breadth import analyze_asset_breadth

results = analyze_asset_breadth(
    prices,              # DataFrame with prices
    metadata,            # DataFrame with grouping columns
    config=trend_config,
    group_by=['asset_class', 'region']
)

# Access results
latest_breadth = results['latest']
full_history = results['breadth_with_changes']
summary = results['summary']
```

Output metrics:
- `breadth_up`: % of instruments in uptrend
- `breadth_down`: % in downtrend
- `avg_trend_score`: Average trend score
- `median_trend_duration`: Median trend duration
- `breadth_up_change_1m`: 1-month change in breadth (and 3m, 6m, 12m)

### Factor Trends

Analyze Fama-French factor indices:

```python
from src.analysis.factor_trends import analyze_factor_trends

# Load factor returns
factor_returns = pd.read_csv('factor_returns.csv', index_col='date', parse_dates=True)

results = analyze_factor_trends(
    factor_returns,
    market_returns=None,  # Optional market benchmark
    config=trend_config
)

# Access results
latest = results['latest']
full_trends = results['trends']
correlations = results['correlations']
regime_history_HML = results['regime_history_HML']
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/api/asset-breadth/current` | GET | Current breadth for all asset classes |
| `/api/asset-breadth/history` | GET | Historical breadth (filter by asset_class, region) |
| `/api/factor-trends/current` | GET | Current factor trend states |
| `/api/factor-trends/history` | GET | Historical factor trends (filter by factor) |
| `/api/factor-breadth/current` | GET | Current factor breadth metrics |
| `/api/valuation-spreads/current` | GET | Current valuation spreads |
| `/api/config` | GET | Current configuration |

### Example API Responses

**GET `/api/asset-breadth/current`**
```json
{
  "data": [
    {
      "asset_class": "Equity",
      "breadth_up": 0.75,
      "breadth_down": 0.10,
      "avg_trend_score": 0.45,
      "median_trend_duration": 45,
      "breadth_up_change_1m": 0.15,
      "num_instruments": 8
    }
  ],
  "columns": ["asset_class", "breadth_up", ...]
}
```

## Production Deployment

### Batch Processing

Schedule `scripts/compute_batch.py` to run daily:

```bash
# Cron example (runs at 6 AM daily)
0 6 * * * cd /path/to/dashboard && /path/to/venv/bin/python scripts/compute_batch.py >> logs/batch.log 2>&1
```

### API Deployment

#### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t factor-dashboard .
docker run -p 8000:8000 -v $(pwd)/data:/app/data factor-dashboard
```

#### Systemd Service

Create `/etc/systemd/system/factor-dashboard.service`:

```ini
[Unit]
Description=Factor Dashboard API
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/path/to/dashboard
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable factor-dashboard
sudo systemctl start factor-dashboard
```

## Advanced Usage

### Custom Universes

Define custom universes in metadata:

```python
import pandas as pd

metadata = pd.DataFrame({
    'ticker': ['AAPL', 'MSFT', 'GOOGL', ...],
    'asset_class': ['Equity', 'Equity', 'Equity', ...],
    'style': ['Growth', 'Growth', 'Growth', ...],
    'sector': ['Tech', 'Tech', 'Tech', ...],
    'market_cap': ['Large', 'Large', 'Large', ...]
})

# Analyze by custom groupings
results = analyze_asset_breadth(
    prices,
    metadata,
    group_by=['style', 'sector']
)
```

### Custom Thresholds

Set explicit trend state thresholds:

```python
config = TrendConfig(
    short_window=50,
    long_window=200,
    strong_uptrend_threshold=0.15,
    moderate_uptrend_threshold=0.05,
    moderate_downtrend_threshold=-0.05,
    strong_downtrend_threshold=-0.15
)
```

### Factor Breadth at Stock Level

```python
from src.analysis.factor_breadth import compute_factor_breadth

# Load stock prices and factor scores
stock_prices = pd.read_csv('stock_prices.csv', index_col='date', parse_dates=True)
factor_scores = pd.read_csv('factor_scores.csv', index_col='date', parse_dates=True)

breadth = compute_factor_breadth(
    stock_prices,
    factor_scores,
    factor_name='Value',
    top_quantile=0.1,  # Top 10% value stocks
    bottom_quantile=0.1
)
```

## Performance Considerations

- **Batch Mode**: Precompute all metrics and cache for fast API serving
- **Incremental Updates**: For large datasets, implement incremental updates
- **Parallel Processing**: Use multiprocessing for independent instrument/factor analysis
- **Caching**: Cache frequently accessed metrics in memory or Redis

## Troubleshooting

### "No module named 'src'"

Make sure you've installed the package:
```bash
pip install -e .
```

### "Breadth data not found"

Run batch computation first:
```bash
python scripts/compute_batch.py
```

### API returns empty results

Check that data files exist in `data/raw/` and batch processing completed successfully.

### Tests failing

Ensure all dependencies are installed:
```bash
pip install -e ".[dev]"
```

## Contributing

1. Create feature branch
2. Write tests for new functionality
3. Ensure all tests pass: `pytest`
4. Update documentation
5. Submit pull request

## License

MIT License - see LICENSE file for details

## References

- Fama, Eugene F., and Kenneth R. French. "Common risk factors in the returns on stocks and bonds." (1993)
- Technical trend following literature
- Modern portfolio management practices

## Contact

For questions or support, please open an issue on GitHub.
