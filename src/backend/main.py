"""
FastAPI Backend for Multi Asset Factor Dashboard

Serves precomputed metrics via REST API endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
from typing import Optional, List
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DEFAULT_CONFIG
from utils import get_logger

# Import API routers
from backend.api import signals, regimes

# Setup logging
logger = get_logger(__name__)

app = FastAPI(
    title="Multi Asset Factor Trend Dashboard API",
    description="API for serving multi-asset and factor trend analysis with advanced analytics",
    version="0.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signals.router)
app.include_router(regimes.router)

# Data cache directory
CACHE_DIR = Path(DEFAULT_CONFIG.data.cache_dir)


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "message": "Multi Asset Factor Trend Dashboard API",
        "version": "0.1.0",
        "endpoints": {
            "/health": "Health check",
            "/api/asset-breadth/current": "Current asset class breadth",
            "/api/asset-breadth/history": "Historical breadth for an asset class",
            "/api/factor-trends/current": "Current factor trend states",
            "/api/factor-trends/history": "Historical trends for a factor",
            "/api/factor-breadth/current": "Current factor breadth metrics",
            "/api/signals/breadth": "Breadth-based trading signals",
            "/api/signals/momentum": "Momentum-based signals",
            "/api/signals/factors": "Factor tilt signals",
            "/api/signals/all": "All signals",
            "/api/regimes/current": "Current market regimes",
            "/api/regimes/trend": "Trend regime analysis",
            "/api/regimes/volatility": "Volatility regime analysis",
            "/api/regimes/risk": "Risk-on/risk-off regime",
            "/api/valuation-spreads/current": "Current valuation spreads",
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/asset-breadth/current")
def get_current_asset_breadth():
    """
    Get current breadth metrics for all asset classes.

    Returns summary table with latest breadth metrics.
    """
    try:
        # Load precomputed data
        breadth_file = CACHE_DIR / "asset_breadth_latest.parquet"

        if not breadth_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Breadth data not found. Run batch computation first."
            )

        df = pd.read_parquet(breadth_file)

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/asset-breadth/history")
def get_asset_breadth_history(
    asset_class: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 252
):
    """
    Get historical breadth metrics.

    Parameters:
    - asset_class: Filter by asset class
    - region: Filter by region
    - limit: Number of most recent records to return (default 252)
    """
    try:
        breadth_file = CACHE_DIR / "asset_breadth_full.parquet"

        if not breadth_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Breadth history not found. Run batch computation first."
            )

        df = pd.read_parquet(breadth_file)

        # Apply filters
        if asset_class:
            df = df[df['asset_class'] == asset_class]
        if region:
            df = df[df['region'] == region]

        # Get most recent records
        df = df.sort_values('date').tail(limit)

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factor-trends/current")
def get_current_factor_trends():
    """Get current trend state for all factors."""
    try:
        trends_file = CACHE_DIR / "factor_trends_latest.parquet"

        if not trends_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Factor trends not found. Run batch computation first."
            )

        df = pd.read_parquet(trends_file)

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factor-trends/history")
def get_factor_trends_history(
    factor: str,
    limit: int = 252
):
    """
    Get historical trends for a specific factor.

    Parameters:
    - factor: Factor name (e.g., HML, SMB, MOM)
    - limit: Number of most recent records
    """
    try:
        trends_file = CACHE_DIR / "factor_trends_full.parquet"

        if not trends_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Factor trends history not found."
            )

        df = pd.read_parquet(trends_file)
        df = df[df['factor'] == factor]
        df = df.sort_values('date').tail(limit)

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/factor-breadth/current")
def get_current_factor_breadth(factor: Optional[str] = None):
    """Get current factor breadth metrics."""
    try:
        breadth_file = CACHE_DIR / "factor_breadth_latest.parquet"

        if not breadth_file.exists():
            # Return empty if not computed
            return {"data": [], "columns": []}

        df = pd.read_parquet(breadth_file)

        if factor:
            df = df[df['factor'] == factor]

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/valuation-spreads/current")
def get_current_valuation_spreads():
    """Get current valuation spreads for factors."""
    try:
        spreads_file = CACHE_DIR / "valuation_spreads_latest.parquet"

        if not spreads_file.exists():
            return {"data": [], "columns": []}

        df = pd.read_parquet(spreads_file)

        return {
            "data": df.to_dict(orient="records"),
            "columns": list(df.columns)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
def get_config():
    """Get current configuration."""
    return {
        "trend_engine": DEFAULT_CONFIG.trend_engine.__dict__,
        "breadth": DEFAULT_CONFIG.breadth.__dict__,
        "factor": DEFAULT_CONFIG.factor.__dict__,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
