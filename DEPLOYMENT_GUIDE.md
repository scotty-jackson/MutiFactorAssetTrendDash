# Deployment Guide - Multi Asset Factor Trend Dashboard v0.2.0

## Quick Start Options

### Option 1: Docker Compose (Recommended for Production)

**Start the entire stack with one command:**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Access the API
curl http://localhost:8000/health

# Interactive API docs
open http://localhost:8000/docs

# Stop all services
docker-compose down
```

**What gets deployed:**
- PostgreSQL/TimescaleDB (port 5432)
- Redis cache (port 6379)
- FastAPI backend (port 8000)
- Batch computation worker
- Nginx reverse proxy (port 80) - when using `--profile production`

### Option 2: Local Development

```bash
# 1. Install dependencies
pip install -e .
pip install -e ".[dev]"

# 2. Generate sample data
python -c "from src.data.loaders import generate_sample_data; generate_sample_data()"

# 3. Run batch computation
python scripts/compute_batch.py

# 4. Start API server
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

# 5. Access API
curl http://localhost:8000/api/asset-breadth/current
```

### Option 3: Production with Custom Configuration

```bash
# 1. Set environment variables
export DATABASE_URL="postgresql://user:pass@host:5432/dashboard"
export REDIS_URL="redis://host:6379/0"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_USERNAME="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# 2. Start with production profile
docker-compose --profile production up -d

# 3. Scale API horizontally
docker-compose up --scale api=3 -d
```

## Configuration

### Environment Variables

Create `.env` file:
```bash
# Database
DATABASE_URL=postgresql://dashboard_user:password@postgres:5432/factor_dashboard

# Cache
REDIS_URL=redis://redis:6379/0

# Email Alerts
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your_app_password
ALERT_FROM_ADDRESS=alerts@yourdomain.com
ALERT_TO_ADDRESSES=trader1@yourdomain.com,trader2@yourdomain.com

# Slack Alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Data Directories
DATA_DIR=/app/data
CACHE_DIR=/app/data/cache
LOG_DIR=/app/logs
```

### Alert Configuration

Create `config/alerts.yaml`:
```yaml
email:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  from_address: alerts@yourdomain.com
  to_addresses:
    - trader@yourdomain.com
    - pm@yourdomain.com

slack:
  enabled: true
  webhook_url: https://hooks.slack.com/services/...
  channel: "#trading-alerts"

signals:
  min_confidence_for_alert: 0.7
  alert_on_types:
    - STRONG_BUY
    - STRONG_SELL

regimes:
  alert_on_change: true
  min_confidence: 0.6
```

## Database Setup

### Initialize Database

```bash
# Using Docker
docker-compose up postgres -d
docker-compose exec postgres psql -U dashboard_user -d factor_dashboard -f /docker-entrypoint-initdb.d/init.sql

# Manual setup
psql -U your_user -d factor_dashboard -f scripts/init_db.sql
```

### Verify Database

```bash
docker-compose exec postgres psql -U dashboard_user -d factor_dashboard -c "\dt"

# Should show tables:
# price_data
# trend_metrics
# breadth_metrics
# factor_trends
# signals
# alerts
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connection
docker-compose exec postgres pg_isready

# Redis connection
docker-compose exec redis redis-cli ping
```

### Metrics

```bash
# View collected metrics
cat logs/metrics/metrics_$(date +%Y%m%d_%H).jsonl

# Alert history
cat logs/alerts/alerts_$(date +%Y%m%d).log

# API logs
docker-compose logs api | tail -100
```

### Dashboards

Connect to metrics with:
- Grafana (recommended)
- Prometheus
- Datadog
- New Relic

Example Grafana dashboard:
```bash
# Import metrics to Grafana
# Use the JSON files in grafana/ directory (coming soon)
```

## Scheduled Tasks

### Cron Setup (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add batch computation (runs at 6 AM daily)
0 6 * * * cd /path/to/dashboard && /path/to/venv/bin/python scripts/compute_batch.py >> logs/batch.log 2>&1

# Add alert check (runs every hour)
0 * * * * cd /path/to/dashboard && /path/to/venv/bin/python scripts/check_alerts.py >> logs/alerts_check.log 2>&1
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: factor-dashboard-batch
spec:
  schedule: "0 6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: batch-worker
            image: factor-dashboard:latest
            command: ["python", "scripts/compute_batch.py"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: dashboard-secrets
                  key: database-url
          restartPolicy: OnFailure
```

## Scaling

### Horizontal Scaling

```bash
# Scale API instances
docker-compose up --scale api=5 -d

# Load balance with nginx
# nginx.conf already configured for upstream load balancing
```

### Database Optimization

```sql
-- Create additional indexes
CREATE INDEX idx_breadth_date_class ON breadth_metrics(time, asset_class);
CREATE INDEX idx_signals_confidence ON signals(confidence DESC);

-- Analyze tables
ANALYZE price_data;
ANALYZE trend_metrics;
ANALYZE breadth_metrics;

-- Check compression status
SELECT * FROM timescaledb_information.compressed_chunk_stats;
```

## Backup & Recovery

### Database Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U dashboard_user factor_dashboard > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T postgres psql -U dashboard_user factor_dashboard < backup_20231201.sql
```

### Data Backup

```bash
# Backup data directory
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/

# Restore
tar -xzf data_backup_20231201.tar.gz
```

## Security

### Production Checklist

- [ ] Change default database password
- [ ] Enable SSL/TLS for database connections
- [ ] Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable API authentication (add middleware)
- [ ] Configure rate limiting
- [ ] Set up firewall rules
- [ ] Enable HTTPS (nginx SSL)
- [ ] Rotate credentials regularly
- [ ] Monitor access logs
- [ ] Set up intrusion detection

### API Authentication (Optional)

Add to `src/backend/main.py`:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.get("/api/protected")
async def protected_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Verify token
    if verify_token(credentials.credentials):
        return {"message": "Authorized"}
    raise HTTPException(status_code=401, detail="Unauthorized")
```

## Troubleshooting

### Common Issues

**API returns 404 for breadth data**
```bash
# Run batch computation
python scripts/compute_batch.py

# Check cache directory
ls -lah data/cache/
```

**Database connection refused**
```bash
# Check postgres is running
docker-compose ps postgres

# Check connection string
docker-compose exec api env | grep DATABASE_URL
```

**High memory usage**
```bash
# Check container stats
docker stats

# Limit container memory
docker-compose up -d --scale api=1 --memory="2g"
```

**Slow API responses**
```bash
# Enable Redis caching
# Check redis is running
docker-compose ps redis

# Monitor cache hit rate
docker-compose exec redis redis-cli INFO stats | grep hits
```

## Performance Tuning

### Database

```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '256MB';

-- Reload config
SELECT pg_reload_conf();
```

### API

```python
# Add to main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis:6379")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

### Worker

```bash
# Run multiple workers in parallel
python scripts/compute_batch.py --parallel --workers 4
```

## Monitoring Alerts

### Set Up Email Alerts

```python
from monitoring.alerts import AlertManager, Alert, AlertType, AlertChannel

manager = AlertManager(
    email_config={
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'alerts@yourdomain.com',
        'password': 'app_password',
        'from_address': 'alerts@yourdomain.com',
        'to_addresses': ['trader@yourdomain.com']
    }
)

# Send test alert
alert = Alert(
    title="Test Alert",
    message="System is operational",
    alert_type=AlertType.INFO,
    timestamp=datetime.now(),
    metadata={},
    channels=[AlertChannel.EMAIL]
)

manager.send_alert(alert)
```

### Set Up Slack Alerts

```python
manager = AlertManager(
    slack_config={
        'webhook_url': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    }
)
```

## Production Deployment Checklist

- [ ] Environment variables configured
- [ ] Database initialized and tested
- [ ] Redis cache running
- [ ] Sample data loaded
- [ ] Batch computation successful
- [ ] API health check passing
- [ ] Alert system configured and tested
- [ ] Logging configured
- [ ] Metrics collection enabled
- [ ] Backups scheduled
- [ ] Monitoring dashboards set up
- [ ] Security hardening complete
- [ ] Load testing performed
- [ ] Documentation reviewed
- [ ] Team training completed

## Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Review health checks: `curl http://localhost:8000/health`
3. Verify data: `ls -lah data/cache/`
4. Check GitHub issues
5. Contact support team

---

**Ready to deploy?**

```bash
git clone <repo>
cd MutiFactorAssetTrendDash
docker-compose up -d
curl http://localhost:8000/docs
```

That's it! You're running a production-grade quantitative analysis platform.
