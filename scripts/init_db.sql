-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Price data table
CREATE TABLE IF NOT EXISTS price_data (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(50) NOT NULL,
    close DOUBLE PRECISION,
    volume BIGINT,
    PRIMARY KEY (time, ticker)
);

-- Convert to hypertable
SELECT create_hypertable('price_data', 'time', if_not_exists => TRUE);

-- Trend metrics table
CREATE TABLE IF NOT EXISTS trend_metrics (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(50) NOT NULL,
    trend_score DOUBLE PRECISION,
    trend_state INTEGER,
    trend_duration INTEGER,
    ma_50 DOUBLE PRECISION,
    ma_200 DOUBLE PRECISION,
    PRIMARY KEY (time, ticker)
);

SELECT create_hypertable('trend_metrics', 'time', if_not_exists => TRUE);

-- Breadth metrics table
CREATE TABLE IF NOT EXISTS breadth_metrics (
    time TIMESTAMPTZ NOT NULL,
    asset_class VARCHAR(50) NOT NULL,
    breadth_up DOUBLE PRECISION,
    breadth_down DOUBLE PRECISION,
    breadth_neutral DOUBLE PRECISION,
    avg_trend_score DOUBLE PRECISION,
    num_instruments INTEGER,
    PRIMARY KEY (time, asset_class)
);

SELECT create_hypertable('breadth_metrics', 'time', if_not_exists => TRUE);

-- Factor trends table
CREATE TABLE IF NOT EXISTS factor_trends (
    time TIMESTAMPTZ NOT NULL,
    factor VARCHAR(50) NOT NULL,
    index_level DOUBLE PRECISION,
    trend_score DOUBLE PRECISION,
    trend_state INTEGER,
    trend_duration INTEGER,
    PRIMARY KEY (time, factor)
);

SELECT create_hypertable('factor_trends', 'time', if_not_exists => TRUE);

-- Signals table
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    instrument VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    signal VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_time ON signals (time DESC);
CREATE INDEX idx_signals_instrument ON signals (instrument);
CREATE INDEX idx_signals_type ON signals (signal_type);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    alert_type VARCHAR(20),
    metadata JSONB,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_time ON alerts (time DESC);
CREATE INDEX idx_alerts_sent ON alerts (sent);

-- Create compression policy (keep uncompressed data for 7 days)
SELECT add_compression_policy('price_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('trend_metrics', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('breadth_metrics', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('factor_trends', INTERVAL '7 days', if_not_exists => TRUE);

-- Create retention policy (keep data for 5 years)
SELECT add_retention_policy('price_data', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('trend_metrics', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('breadth_metrics', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('factor_trends', INTERVAL '5 years', if_not_exists => TRUE);

-- Continuous aggregates for performance
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    ticker,
    FIRST(close, time) AS open,
    MAX(close) AS high,
    MIN(close) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM price_data
GROUP BY bucket, ticker;

SELECT add_continuous_aggregate_policy('price_data_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
