"""Logging and tracing utilities for debugging RAG workflow."""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from functools import wraps


class WorkflowTracer:
    """Tracer for logging workflow execution steps."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("logs/traces")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.traces: List[Dict] = []
        self.current_trace_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def log_step(
        self,
        step_name: str,
        input_data: Any,
        output_data: Any,
        duration_ms: float,
        metadata: Dict | None = None
    ):
        """Log a workflow step."""
        trace_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step_name,
            "duration_ms": round(duration_ms, 2),
            "input_summary": self._summarize(input_data),
            "output_summary": self._summarize(output_data),
            "metadata": metadata or {}
        }
        self.traces.append(trace_entry)
        self._print_trace(trace_entry)

    def _summarize(self, data: Any) -> str:
        """Create summary of data for logging."""
        if isinstance(data, str):
            return f"<str len={len(data)}>"
        elif isinstance(data, list):
            return f"<list len={len(data)}>"
        elif isinstance(data, dict):
            return f"<dict keys={list(data.keys())}>"
        else:
            return str(type(data).__name__)

    def _print_trace(self, entry: Dict):
        """Print trace entry to console."""
        print(f"\n[TRACE] {entry['step']} ({entry['duration_ms']}ms)")
        print(f"  Input: {entry['input_summary']}")
        print(f"  Output: {entry['output_summary']}")
        if entry['metadata']:
            print(f"  Metadata: {entry['metadata']}")

    def save(self, filename: str | None = None):
        """Save traces to JSON file."""
        if not filename:
            filename = f"trace_{self.current_trace_id}.json"

        output_path = self.output_dir / filename
        output = {
            "trace_id": self.current_trace_id,
            "total_steps": len(self.traces),
            "total_duration_ms": sum(t["duration_ms"] for t in self.traces),
            "steps": self.traces
        }
        output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"\n[TRACE] Saved to: {output_path}")

    def clear(self):
        """Clear current traces."""
        self.traces = []
        self.current_trace_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def trace_step(step_name: str, tracer: WorkflowTracer | None = None):
    """Decorator to trace workflow step execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if tracer is None:
                return func(*args, **kwargs)

            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Extract metadata from result if it's a WorkflowState
            metadata = {}
            if hasattr(result, 'metadata'):
                metadata = {k: v for k, v in result.metadata.items() if k != "query_embedding"}

            tracer.log_step(
                step_name=step_name,
                input_data=args[0] if args else kwargs,
                output_data=result,
                duration_ms=duration_ms,
                metadata=metadata
            )

            return result
        return wrapper
    return decorator


class RetrievalLogger:
    """Logger for detailed retrieval debugging."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("logs/retrieval")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log_retrieval(
        self,
        query: str,
        embedding: List[float],
        retrieved_docs: List[Dict],
        filter_used: Dict | None,
        reranked: bool
    ):
        """Log detailed retrieval information."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "embedding_dim": len(embedding),
            "embedding_norm": round(sum(x**2 for x in embedding) ** 0.5, 3),
            "filter": filter_used,
            "num_retrieved": len(retrieved_docs),
            "reranked": reranked,
            "documents": [
                {
                    "rank": i + 1,
                    "id": doc.get("_id"),
                    "text_preview": doc.get("text", "")[:200],
                    "node_type": doc.get("node_type")
                }
                for i, doc in enumerate(retrieved_docs[:10])  # Top 10 only
            ]
        }

        output_path = self.output_dir / f"retrieval_{timestamp}.json"
        output_path.write_text(json.dumps(log_entry, indent=2), encoding="utf-8")
        print(f"[RETRIEVAL LOG] Saved to: {output_path}")


class GenerationLogger:
    """Logger for generation debugging."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("logs/generation")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log_generation(
        self,
        query: str,
        prompt: str,
        response: str,
        context_items: List[str],
        duration_ms: float
    ):
        """Log detailed generation information."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "num_context_items": len(context_items),
            "duration_ms": round(duration_ms, 2),
            "prompt": prompt,
            "response": response,
            "context_previews": [ctx[:200] for ctx in context_items]
        }

        output_path = self.output_dir / f"generation_{timestamp}.json"
        output_path.write_text(json.dumps(log_entry, indent=2), encoding="utf-8")
        print(f"[GENERATION LOG] Saved to: {output_path}")
