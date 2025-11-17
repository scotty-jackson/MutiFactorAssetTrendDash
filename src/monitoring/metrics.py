"""
Metrics Collection

Track system performance and business metrics.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class Metric:
    """A single metric measurement."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collect and store system metrics."""

    def __init__(self, flush_interval: int = 60):
        """
        Initialize metrics collector.

        Parameters
        ----------
        flush_interval : int
            Seconds between metric flushes to disk
        """
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.flush_interval = flush_interval
        self.last_flush = time.time()

    def record(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric.

        Parameters
        ----------
        name : str
            Metric name (e.g., 'api.request.duration')
        value : float
            Metric value
        tags : dict, optional
            Tags for filtering/grouping
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )

        self.metrics[name].append(metric)

        # Auto-flush if needed
        if time.time() - self.last_flush > self.flush_interval:
            self.flush()

    def increment(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self.record(name, 1.0, tags)

    def timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric."""
        self.record(f"{name}.duration_ms", duration_ms, tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a gauge metric (current value)."""
        self.record(f"{name}.gauge", value, tags)

    def get_stats(self, name: str, window_seconds: int = 3600) -> Dict:
        """
        Get statistics for a metric.

        Parameters
        ----------
        name : str
            Metric name
        window_seconds : int
            Time window for stats

        Returns
        -------
        stats : dict
            Statistics (count, mean, min, max, p50, p95, p99)
        """
        if name not in self.metrics:
            return {}

        cutoff = datetime.now().timestamp() - window_seconds
        recent = [
            m for m in self.metrics[name]
            if m.timestamp.timestamp() >= cutoff
        ]

        if not recent:
            return {}

        values = [m.value for m in recent]
        values_sorted = sorted(values)

        stats = {
            'count': len(values),
            'sum': sum(values),
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'p50': values_sorted[len(values) // 2],
            'p95': values_sorted[int(len(values) * 0.95)],
            'p99': values_sorted[int(len(values) * 0.99)]
        }

        return stats

    def flush(self, filepath: Optional[str] = None):
        """
        Flush metrics to disk.

        Parameters
        ----------
        filepath : str, optional
            Path to write metrics (default: logs/metrics/)
        """
        if filepath is None:
            metrics_dir = Path("logs/metrics")
            metrics_dir.mkdir(parents=True, exist_ok=True)
            filepath = metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"

        with open(filepath, 'a') as f:
            for name, metric_list in self.metrics.items():
                for metric in metric_list:
                    record = {
                        'name': metric.name,
                        'value': metric.value,
                        'timestamp': metric.timestamp.isoformat(),
                        'tags': metric.tags
                    }
                    f.write(json.dumps(record) + '\n')

        # Clear metrics after flush
        self.metrics.clear()
        self.last_flush = time.time()

    def summary(self) -> Dict:
        """Get summary of all metrics."""
        summary = {}

        for name in self.metrics.keys():
            summary[name] = self.get_stats(name)

        return summary


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Decorator for timing functions
import functools


def track_timing(metric_name: str):
    """Decorator to track function execution time."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                get_metrics_collector().timing(metric_name, duration_ms, {'status': 'success'})
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                get_metrics_collector().timing(metric_name, duration_ms, {'status': 'error'})
                raise
        return wrapper
    return decorator
