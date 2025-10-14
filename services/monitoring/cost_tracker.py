"""Cost tracking for LLM token usage and estimated costs.

Tracks token usage from watsonx.ai API responses and estimates costs
based on model pricing. Supports per-use-case model configuration from
ADR-007-003 (cost-performance trade-off framework).

Pricing data from E-007-006 (LLM cost management, 30x price differences).
"""

from typing import Any, Dict, Optional

from services.monitoring.metrics_collector import MetricsCollector


class CostTracker:
    """Track LLM token usage and estimated costs.

    Integrates with watsonx.ai response metadata to extract token counts
    and estimate costs based on model-specific pricing.

    Usage:
        tracker = CostTracker(metrics_collector)

        # After LLM API call:
        tracker.log_llm_call(
            model_id="ibm/granite-13b-instruct-v2",
            input_tokens=150,
            output_tokens=80,
            metadata={"step": "reasoning", "query_type": "simple"}
        )

    Pricing Notes:
        - Prices are approximate and may vary by watsonx.ai instance/region
        - Update WATSONX_COST_PER_1K_TOKENS when pricing changes
        - Default fallback: $0.002 per 1K tokens (granite-13b baseline)
    """

    # Pricing per 1K tokens (input + output combined)
    # Source: watsonx.ai pricing (approximate, varies by instance)
    WATSONX_COST_PER_1K_TOKENS = {
        # Current model (deprecated)
        "ibm/granite-13b-instruct-v2": 0.002,  # $0.002 per 1K tokens

        # Newer Granite 3.x models (smaller, faster, cheaper)
        "ibm/granite-3-3-8b-instruct": 0.001,   # Estimated $0.001 per 1K tokens
        "ibm/granite-3-1-8b-instruct": 0.001,   # Estimated $0.001 per 1K tokens
        "ibm/granite-3-0-8b-instruct": 0.001,   # Estimated $0.001 per 1K tokens

        # Chat variants
        "ibm/granite-13b-chat-v2": 0.002,       # $0.002 per 1K tokens
        "ibm/granite-3-3-8b-chat": 0.001,       # Estimated $0.001 per 1K tokens

        # Other models (for comparison)
        "meta-llama/llama-2-70b-chat": 0.004,   # Larger models more expensive
        "mistralai/mixtral-8x7b-instruct": 0.002,
    }

    DEFAULT_COST_PER_1K = 0.002  # Fallback for unknown models

    def __init__(self, collector: MetricsCollector):
        """Initialize cost tracker.

        Args:
            collector: MetricsCollector instance to log metrics to
        """
        self.collector = collector

    def log_llm_call(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """Log LLM API call with token usage and estimated cost.

        Args:
            model_id: Watsonx.ai model ID (e.g., "ibm/granite-13b-instruct-v2")
            input_tokens: Number of input tokens (prompt)
            output_tokens: Number of output tokens (generated response)
            metadata: Additional context (step, query_type, use_case, etc.)

        Returns:
            Estimated cost in USD

        Example:
            cost = tracker.log_llm_call(
                model_id="ibm/granite-13b-instruct-v2",
                input_tokens=150,
                output_tokens=80,
                metadata={
                    "step": "reasoning",
                    "query_type": "simple",
                    "use_case": "reasoning"
                }
            )
        """
        total_tokens = input_tokens + output_tokens

        # Get cost per 1K tokens for this model
        cost_per_1k = self.WATSONX_COST_PER_1K_TOKENS.get(
            model_id,
            self.DEFAULT_COST_PER_1K
        )

        # Calculate estimated cost
        estimated_cost = (total_tokens / 1000.0) * cost_per_1k

        # Prepare metadata
        log_metadata = {
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_per_1k_tokens": cost_per_1k,
            **(metadata or {})
        }

        # Log to metrics collector
        self.collector.log_metric(
            metric_type="cost",
            metric_name="llm_api_call",
            value=estimated_cost,
            metadata=log_metadata
        )

        return estimated_cost

    def log_embedding_call(
        self,
        model_id: str,
        num_texts: int,
        avg_text_length: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """Log embedding API call (typically cheaper than generation).

        Args:
            model_id: Embedding model ID (e.g., "ibm/slate-125m-english-rtrvr")
            num_texts: Number of texts embedded
            avg_text_length: Average text length in characters
            metadata: Additional context

        Returns:
            Estimated cost in USD (typically very low for embeddings)

        Note:
            Embedding costs are typically 10-100x cheaper than generation.
            Using conservative estimate: $0.0001 per embedding call.
        """
        # Embedding pricing is typically much lower
        # Conservative estimate: $0.0001 per embedding
        estimated_cost = num_texts * 0.0001

        log_metadata = {
            "model_id": model_id,
            "num_texts": num_texts,
            "avg_text_length": avg_text_length,
            "operation": "embedding",
            **(metadata or {})
        }

        self.collector.log_metric(
            metric_type="cost",
            metric_name="embedding_api_call",
            value=estimated_cost,
            metadata=log_metadata
        )

        return estimated_cost

    def get_total_cost(self) -> float:
        """Get total estimated cost from all logged LLM calls.

        Returns:
            Total estimated cost in USD

        Usage:
            total = tracker.get_total_cost()
            print(f"Total LLM cost this session: ${total:.4f}")
        """
        cost_metrics = self.collector.get_metrics(metric_type="cost")
        return sum(m["value"] for m in cost_metrics)

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model ID.

        Returns:
            Dict mapping model_id to total cost

        Usage:
            by_model = tracker.get_cost_by_model()
            for model, cost in by_model.items():
                print(f"{model}: ${cost:.4f}")
        """
        cost_metrics = self.collector.get_metrics(metric_type="cost")

        by_model: Dict[str, float] = {}
        for metric in cost_metrics:
            model_id = metric["metadata"].get("model_id", "unknown")
            by_model[model_id] = by_model.get(model_id, 0.0) + metric["value"]

        return by_model

    def get_cost_by_use_case(self) -> Dict[str, float]:
        """Get cost breakdown by use case (reasoning, orchestrator, etc.).

        Returns:
            Dict mapping use_case to total cost

        Usage:
            by_use_case = tracker.get_cost_by_use_case()
            print(f"Reasoning cost: ${by_use_case.get('reasoning', 0):.4f}")
        """
        cost_metrics = self.collector.get_metrics(metric_type="cost")

        by_use_case: Dict[str, float] = {}
        for metric in cost_metrics:
            use_case = metric["metadata"].get("use_case", "unknown")
            by_use_case[use_case] = by_use_case.get(use_case, 0.0) + metric["value"]

        return by_use_case
