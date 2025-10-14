"""Context manager for automatic latency tracking.

ADR-007-002: Context manager pattern chosen for clean integration and
automatic timing (no manual start/stop required).

Usage:
    from services.monitoring import get_metrics_collector, LatencyTracker

    collector = get_metrics_collector()

    with LatencyTracker(collector, "embedding_step", {"query": "test"}):
        # ... perform embedding operation ...
        pass
    # Latency automatically logged on exit
"""

import time
from typing import Any, Dict, Optional

from services.monitoring.metrics_collector import MetricsCollector


class LatencyTracker:
    """Context manager for automatic latency tracking.

    Automatically records start time on entry and logs latency metric on exit.
    Handles exceptions gracefully (still logs latency even if operation fails).

    Usage:
        collector = get_metrics_collector()

        with LatencyTracker(collector, "embedding_step", {"query": "What is porosity?"}):
            embeddings = embed_query(query)
        # Latency automatically logged

        # Also works with workflow steps:
        with LatencyTracker(collector, "reasoning_step", {"query_type": "simple"}):
            result = reasoning_function(state)

    Attributes:
        collector: MetricsCollector instance to log to
        step_name: Name of the operation being timed
        metadata: Additional context for the metric
        start_time: Unix timestamp when operation started (set in __enter__)
    """

    def __init__(
        self,
        collector: MetricsCollector,
        step_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize latency tracker.

        Args:
            collector: MetricsCollector instance to log metrics to
            step_name: Name of operation (e.g., "embedding_step", "retrieval_step")
            metadata: Additional context (query, query_type, model_id, etc.)
        """
        self.collector = collector
        self.step_name = step_name
        self.metadata = metadata or {}
        self.start_time: float = 0.0

    def __enter__(self) -> "LatencyTracker":
        """Start timing on context entry.

        Returns:
            Self (allows assignment: `with LatencyTracker(...) as tracker:`)
        """
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Stop timing and log metric on context exit.

        Args:
            exc_type: Exception type (if exception occurred)
            exc_val: Exception value
            exc_tb: Exception traceback

        Returns:
            False (allows exception to propagate)

        Note:
            Latency is logged even if operation failed (exception occurred).
            Exception info is added to metadata for debugging.
        """
        duration = time.time() - self.start_time

        # Add exception info to metadata if operation failed
        if exc_type is not None:
            self.metadata["error"] = True
            self.metadata["error_type"] = exc_type.__name__
            self.metadata["error_message"] = str(exc_val)
        else:
            self.metadata["error"] = False

        self.collector.log_metric(
            metric_type="latency",
            metric_name=self.step_name,
            value=duration,
            metadata=self.metadata
        )

        # Return False to allow exception to propagate
        return False


class LatencyTrackerNoOp:
    """No-op latency tracker for when monitoring is disabled.

    Provides same interface as LatencyTracker but does nothing.
    Useful for conditional monitoring without code duplication.

    Usage:
        if monitoring_enabled:
            tracker_cls = LatencyTracker
        else:
            tracker_cls = LatencyTrackerNoOp

        with tracker_cls(collector, "step", {}):
            do_work()
    """

    def __init__(self, collector=None, step_name: str = "", metadata=None):
        """Initialize no-op tracker (arguments ignored)."""
        pass

    def __enter__(self):
        """No-op enter."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """No-op exit."""
        return False
