# Quick Start Guide

## What Was Built

A **production-ready** Multi Asset and Factor Trend Dashboard with:

### Core Modules
1. **Trend Engine** - Robust trend analysis with MA, slope, and state classification
2. **Multi-Asset Breadth** - Track breadth across asset classes, regions, sectors
3. **Factor Trends** - Analyze Fama-French factor indices
4. **Factor Breadth** - Within-factor breadth at stock level
5. **Valuation Spreads** - Factor valuation spread analysis
6. **FastAPI Backend** - REST API serving all metrics
7. **Configuration System** - YAML-based, data-driven configuration
8. **Data Loaders** - Flexible CSV loaders with sample data generation

### Key Features
- ✅ Modular, well-documented code
- ✅ Comprehensive test suite (33 tests, all passing)
- ✅ Batch processing for precomputation
- ✅ REST API with interactive docs
- ✅ Production deployment guides
- ✅ No hard-coded parameters - fully configurable

## Get Started in 5 Minutes

### 1. Setup Environment (if not already done)
```bash
cd /home/user/MutiFactorAssetTrendDash
source venv/bin/activate
```

### 2. Generate Sample Data (already done)
```bash
# Sample data already generated in data/raw/
ls data/raw/
# multi_asset_metadata.csv  multi_asset_prices.csv  factor_returns.csv
```

### 3. Run Batch Computation (already done)
```bash
# Metrics already computed and cached
ls data/cache/
# asset_breadth_full.parquet        factor_trends_full.parquet
# asset_breadth_latest.parquet      factor_trends_latest.parquet
# asset_breadth_summary.parquet     factor_correlations.parquet
```

### 4. Start the API Server
```bash
# From project root
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000/docs for interactive API documentation

### 5. Query the API

```bash
# Get current asset breadth
curl http://localhost:8000/api/asset-breadth/current | jq

# Get factor trends
curl http://localhost:8000/api/factor-trends/current | jq

# Get historical breadth for Equity
curl "http://localhost:8000/api/asset-breadth/history?asset_class=Equity" | jq
```

## Project Structure

```
MutiFactorAssetTrendDash/
├── src/
│   ├── trend_engine/         # Core trend analysis engine
│   │   └── trend_engine.py   # MA, slope, state classification, duration
│   ├── analysis/
│   │   ├── multi_asset_breadth.py   # Cross-asset breadth metrics
│   │   ├── factor_trends.py         # Factor index trends
│   │   ├── factor_breadth.py        # Within-factor breadth
│   │   └── valuation_spreads.py     # Valuation spread analysis
│   ├── data/
│   │   └── loaders.py        # CSV loaders, sample data generator
│   ├── config/
│   │   └── config.py         # Configuration management
│   └── backend/
│       └── main.py           # FastAPI server
├── tests/
│   ├── test_trend_engine.py           # 20 tests ✓
│   └── test_multi_asset_breadth.py    # 13 tests ✓
├── scripts/
│   └── compute_batch.py      # Batch processing script
├── data/
│   ├── raw/                  # Input CSV files
│   ├── processed/            # Processed data
│   └── cache/                # Cached computations
├── ARCHITECTURE.md           # System architecture
├── README.md                 # Full documentation
└── QUICKSTART.md            # This file
```

## Using Your Own Data

### Multi-Asset Prices
Replace `data/raw/multi_asset_prices.csv`:
```csv
date,SPY,TLT,GLD,IWM,QQQ
2020-01-01,330.5,140.2,150.3,165.2,220.4
2020-01-02,331.2,140.5,149.8,165.8,221.1
...
```

### Metadata
Replace `data/raw/multi_asset_metadata.csv`:
```csv
ticker,asset_class,region,sector
SPY,Equity,US,Broad
TLT,Bond,US,LongTerm
GLD,Commodity,Global,Precious
...
```

### Factor Returns
Replace `data/raw/factor_returns.csv`:
```csv
date,HML,SMB,MOM,RMW,CMA
20200101,0.15,0.08,-0.12,0.05,0.03
20200102,-0.08,0.12,0.18,-0.02,0.01
...
```

Then rerun:
```bash
python scripts/compute_batch.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | API info and endpoint list |
| `/health` | Health check |
| `/api/asset-breadth/current` | Current breadth for all asset classes |
| `/api/asset-breadth/history` | Historical breadth (filter by asset_class, region) |
| `/api/factor-trends/current` | Current factor trend states |
| `/api/factor-trends/history` | Historical factor trends (filter by factor) |
| `/api/factor-breadth/current` | Current factor breadth metrics |
| `/api/valuation-spreads/current` | Current valuation spreads |
| `/api/config` | Current configuration |

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Specific module
pytest tests/test_trend_engine.py -v
```

Current status: **33/33 tests passing** ✓

## Next Steps

### 1. Add Your Data
- Replace sample data with your actual data sources
- Update metadata with your universe definitions

### 2. Customize Configuration
Create `config/config.yaml`:
```yaml
trend_engine:
  short_window: 50
  long_window: 200

breadth:
  min_instruments_per_group: 5

factor:
  rebalance_freq: M  # Monthly
```

### 3. Schedule Batch Jobs
```bash
# Add to crontab (runs at 6 AM daily)
0 6 * * * cd /path/to/dashboard && /path/to/venv/bin/python scripts/compute_batch.py
```

### 4. Deploy API
See README.md for Docker and systemd deployment options

### 5. Build Frontend (Optional)
- The API is ready for any frontend (React, Vue, Plotly Dash)
- All endpoints return JSON with data and column metadata
- CORS is enabled for cross-origin requests

## Common Commands

```bash
# Regenerate sample data
python -c "from src.data.loaders import generate_sample_data; generate_sample_data()"

# Run batch computation
python scripts/compute_batch.py

# Start API server
uvicorn src.backend.main:app --reload

# Run tests
pytest -v

# Check test coverage
pytest --cov=src --cov-report=html
```

## Troubleshooting

**Q: API returns 404 for breadth data**
A: Run `python scripts/compute_batch.py` first to generate cached data

**Q: Import errors**
A: Make sure you installed the package: `pip install -e .`

**Q: Tests failing**
A: Install dev dependencies: `pip install -e ".[dev]"`

## Documentation

- `README.md` - Complete documentation
- `ARCHITECTURE.md` - System design and data flow
- API docs - http://localhost:8000/docs (when server is running)

## What Makes This Production-Ready

✅ **Modular Design** - Clean separation of concerns
✅ **Data-Driven** - No hard-coded constants
✅ **Well-Tested** - 33 tests with good coverage
✅ **Documented** - Comprehensive docs and docstrings
✅ **Configurable** - YAML configuration system
✅ **Efficient** - Batch processing with caching
✅ **Extensible** - Easy to add new assets, factors, metrics
✅ **Deployable** - Docker and systemd guides included

## Support

For issues or questions:
1. Check README.md troubleshooting section
2. Review test files for usage examples
3. Examine docstrings in source code
4. Open a GitHub issue

---

Built with Python, FastAPI, pandas, and pytest.
All code committed to branch: `claude/multi-asset-factor-dashboard-01ReH3SpSn9ZTqhDXeWqvCr8`
