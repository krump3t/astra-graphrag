"""Singleton metrics collector for unified telemetry.

Implements MELT-inspired design (Metrics, Events, Logs) from E-007-004.
Thread-safe metric collection with async file writing to minimize overhead.

ADR-007-001: Singleton pattern chosen for global access without DI complexity.
Target overhead: <5ms per metric log operation.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class MetricsCollector:
    """Singleton metrics collector with thread-safe logging.

    Collects four types of metrics:
    1. latency: Step-by-step timing (embedding, retrieval, reasoning, generation)
    2. cost: LLM token usage and estimated costs
    3. cache: Cache hit/miss rates for Redis and glossary
    4. orchestrator: LocalOrchestrator invocations, success rate, term extraction

    Usage:
        collector = get_metrics_collector()
        collector.log_metric("latency", "embedding_step", 0.125, {"query": "test"})
        collector.flush(Path("logs/metrics.json"))
    """

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsCollector":
        """Singleton pattern: ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize metrics storage (only runs once due to singleton)."""
        if self._initialized:
            return

        self.metrics: List[Dict[str, Any]] = []
        self.metrics_lock = threading.Lock()
        self._initialized = True

    def log_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a metric with thread-safe storage.

        Args:
            metric_type: One of "latency", "cost", "cache", "orchestrator"
            metric_name: Specific metric name (e.g., "embedding_step", "llm_api_call")
            value: Numeric metric value (seconds for latency, dollars for cost)
            metadata: Additional context (query, model_id, etc.)

        Example:
            collector.log_metric(
                metric_type="latency",
                metric_name="embedding_step",
                value=0.125,
                metadata={"query": "What is porosity?", "query_type": "simple"}
            )
        """
        with self.metrics_lock:
            metric_entry = {
                "timestamp": time.time(),
                "timestamp_iso": datetime.utcnow().isoformat() + "Z",
                "type": metric_type,
                "name": metric_name,
                "value": value,
                "metadata": metadata or {}
            }
            self.metrics.append(metric_entry)

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve metrics, optionally filtered by type and/or name.

        Args:
            metric_type: Filter by metric type (e.g., "latency")
            metric_name: Filter by metric name (e.g., "embedding_step")

        Returns:
            List of metric entries matching filters
        """
        with self.metrics_lock:
            filtered = self.metrics.copy()

        if metric_type:
            filtered = [m for m in filtered if m["type"] == metric_type]

        if metric_name:
            filtered = [m for m in filtered if m["name"] == metric_name]

        return filtered

    def flush(self, filepath: Path) -> None:
        """Write all metrics to JSON file.

        Args:
            filepath: Path to output JSON file (e.g., logs/metrics.json)

        Note:
            This operation is NOT thread-safe during write. Call after workflow completion.
        """
        with self.metrics_lock:
            metrics_copy = self.metrics.copy()

        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics_copy, f, indent=2, ensure_ascii=False)

    def flush_by_type(self, base_dir: Path) -> Dict[str, Path]:
        """Write metrics to separate files per type.

        Args:
            base_dir: Base directory for metric files (e.g., logs/)

        Returns:
            Dict mapping metric type to filepath written

        Example:
            paths = collector.flush_by_type(Path("logs"))
            # Creates: logs/metrics_latency.json, logs/metrics_cost.json, etc.
        """
        base_dir.mkdir(parents=True, exist_ok=True)

        with self.metrics_lock:
            metrics_by_type = {}
            for metric in self.metrics:
                mtype = metric["type"]
                if mtype not in metrics_by_type:
                    metrics_by_type[mtype] = []
                metrics_by_type[mtype].append(metric)

        written_paths = {}
        for mtype, metrics_list in metrics_by_type.items():
            filepath = base_dir / f"metrics_{mtype}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metrics_list, f, indent=2, ensure_ascii=False)
            written_paths[mtype] = filepath

        return written_paths

    def clear(self) -> None:
        """Clear all metrics (useful for testing)."""
        with self.metrics_lock:
            self.metrics.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for collected metrics.

        Returns:
            Dict with counts by type, total metrics, time range
        """
        with self.metrics_lock:
            if not self.metrics:
                return {
                    "total_metrics": 0,
                    "by_type": {},
                    "time_range": None
                }

            by_type = {}
            for metric in self.metrics:
                mtype = metric["type"]
                by_type[mtype] = by_type.get(mtype, 0) + 1

            timestamps = [m["timestamp"] for m in self.metrics]

            return {
                "total_metrics": len(self.metrics),
                "by_type": by_type,
                "time_range": {
                    "start": min(timestamps),
                    "end": max(timestamps),
                    "duration_seconds": max(timestamps) - min(timestamps)
                }
            }


# Global singleton accessor
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global MetricsCollector singleton instance.

    Returns:
        The singleton MetricsCollector instance

    Usage:
        from services.monitoring import get_metrics_collector

        collector = get_metrics_collector()
        collector.log_metric("latency", "embedding_step", 0.125)
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
