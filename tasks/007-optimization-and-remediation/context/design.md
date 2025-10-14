# Design - Task 007: Optimization & Known Limitations Remediation

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14

---

## Architecture Overview

Task 007 implements **three architectural enhancements**:

1. **Monitoring Infrastructure**: Unified metrics collection (latency, cost, cache, orchestrator telemetry)
2. **Prompt Library**: Centralized prompt management with versioning and templates
3. **LocalOrchestrator Hardening**: Production-grade error handling, retry logic, telemetry

```
┌─────────────────────────────────────────────────────────────┐
│                     GraphRAG Workflow                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Embedding → Retrieval → Reasoning → Generation      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Monitoring Layer (NEW)                      │  │
│  │  - Latency Tracker (per-step timing)                 │  │
│  │  - Cost Tracker (tokens, API calls)                  │  │
│  │  - Cache Metrics (hit rate, evictions)               │  │
│  │  - Orchestrator Telemetry (invocations, success)     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Prompt Library (NEW)                         │  │
│  │  - Templates (chain-of-thought, few-shot)            │  │
│  │  - Reasoning Prompts (domain-specific)               │  │
│  │  - Query Prompts (expansion, rewriting)              │  │
│  │  - Orchestrator Prompts (term extraction)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     LocalOrchestrator (HARDENED)                      │  │
│  │  - Error Handling (timeouts, retries)                │  │
│  │  - Telemetry (success rate, fallback rate)           │  │
│  │  - Optimized Prompts (better term extraction)        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
           ↓
    logs/metrics.json
    logs/cost_metrics.json
    logs/orchestrator_metrics.json
```

---

## Phase 0: Context Scaffolding (2 hours)

**Objective**: Create all SCA v9-Compact required context files

**Deliverables**:
1. `hypothesis.md` - 5 metrics (performance, cost, orchestrator, prompts, observability)
2. `design.md` - This file
3. `evidence.json` - ≥3 P1 sources for optimization strategies
4. `data_sources.json` - Inputs/outputs/transformations
5. `adr.md` - Architectural Decision Records for key choices
6. `risks.md` - Risk assessment + mitigations
7. `assumptions.md` - Validation checklist
8. `glossary.md` - Domain terms
9. `executive_summary.md` - 1-page overview
10. `context_map.md` - Navigation guide
11. `decision_log.md` - Chronological decisions

---

## Phase 1: Instrumentation & Monitoring (3-4 hours)

### 1.1 Monitoring Infrastructure Design

**Objective**: Create unified metrics collection system for latency, cost, cache, and orchestrator telemetry.

**Architecture**:
```python
# services/monitoring/metrics_collector.py
class MetricsCollector:
    """Singleton metrics collector with async file writing."""

    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def log_metric(
        self,
        metric_type: str,  # "latency", "cost", "cache", "orchestrator"
        metric_name: str,
        value: float,
        metadata: Dict[str, Any]
    ):
        \"\"\"Thread-safe metric logging.\"\"\"
        with self.lock:
            self.metrics.append({
                "timestamp": time.time(),
                "type": metric_type,
                "name": metric_name,
                "value": value,
                "metadata": metadata
            })

    def flush(self, filepath: Path):
        \"\"\"Write metrics to JSON file.\"\"\"
        with self.lock:
            with open(filepath, "w") as f:
                json.dump(self.metrics, f, indent=2)
```

**Integration Points**:
1. `workflow.py` - Log query start/end, per-step latency
2. `generation.py` - Log LLM API calls (tokens, cost)
3. `astra_api.py` - Log vector search latency
4. `glossary_cache.py` - Log cache hits/misses
5. `local_orchestrator.py` - Log invocations, success/failure

### 1.2 Latency Tracking

**Design**: Context manager for automatic latency tracking

```python
# services/monitoring/latency_tracker.py
class LatencyTracker:
    \"\"\"Context manager for automatic latency tracking.\"\"\"

    def __init__(self, collector: MetricsCollector, step_name: str, metadata: Dict[str, Any]):
        self.collector = collector
        self.step_name = step_name
        self.metadata = metadata
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.log_metric(
            metric_type="latency",
            metric_name=self.step_name,
            value=duration,
            metadata=self.metadata
        )

# Usage in workflow.py:
def embedding_step(state: WorkflowState) -> WorkflowState:
    with LatencyTracker(metrics_collector, "embedding_step", {"query": state.query}):
        # ... existing embedding logic ...
    return state
```

### 1.3 Cost Tracking

**Design**: Intercept LLM API responses to extract token counts

```python
# services/monitoring/cost_tracker.py
class CostTracker:
    \"\"\"Track LLM token usage and estimated cost.\"\"\"

    WATSONX_COST_PER_1K_TOKENS = {
        "ibm/granite-13b-instruct-v2": 0.002,  # $0.002 per 1K tokens (input+output)
        "ibm/granite-3-3-8b-instruct": 0.001,  # Estimated $0.001 per 1K tokens
    }

    def log_llm_call(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Dict[str, Any]
    ):
        total_tokens = input_tokens + output_tokens
        cost = (total_tokens / 1000) * self.WATSONX_COST_PER_1K_TOKENS.get(model_id, 0.002)

        metrics_collector.log_metric(
            metric_type="cost",
            metric_name="llm_api_call",
            value=cost,
            metadata={
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                **metadata
            }
        )

# Integration in generation.py:
def generate(self, prompt: str, **parameters) -> str:
    # ... existing generation logic ...
    results = payload.get("results") or []
    if results:
        usage = results[0].get("input_token_count", 0), results[0].get("generated_token_count", 0)
        cost_tracker.log_llm_call(self.model_id, usage[0], usage[1], {"step": "generation"})
    return text
```

### 1.4 Orchestrator Telemetry

**Design**: Log all orchestrator operations with success/failure outcomes

```python
# services/orchestration/local_orchestrator.py (additions)
class LocalOrchestrator:
    def invoke(self, query: str, context: str = "") -> Dict[str, Any]:
        metrics_collector.log_metric(
            metric_type="orchestrator",
            metric_name="invocation",
            value=1.0,
            metadata={
                "query_length": len(query),
                "glossary_query_detected": self.is_glossary_query(query)
            }
        )

        # ... existing logic ...

        metrics_collector.log_metric(
            metric_type="orchestrator",
            metric_name="term_extraction",
            value=1.0 if term else 0.0,
            metadata={
                "success": term is not None,
                "term": term,
                "tool_invoked": metadata["mcp_tool_invoked"]
            }
        )
```

---

## Phase 2: LLM Model Selection & Evaluation (2-3 hours)

### 2.1 Model Benchmark Framework

**Objective**: Systematic evaluation of alternative models on representative queries

**Design**:
```python
# scripts/evaluation/model_benchmark.py
class ModelBenchmark:
    \"\"\"Benchmark LLM models on query set.\"\"\"

    MODELS_TO_EVALUATE = [
        "ibm/granite-13b-instruct-v2",  # Current (deprecated)
        "ibm/granite-3-3-8b-instruct",  # Recommended replacement
        "ibm/granite-13b-chat-v2",      # Chat variant
    ]

    def evaluate_model(
        self,
        model_id: str,
        test_queries: List[Dict[str, Any]]  # {"query": "...", "expected_output": "...", "type": "simple"}
    ) -> Dict[str, Any]:
        \"\"\"Evaluate model on test queries, measure latency/cost/accuracy.\"\"\"

        results = []
        for test_case in test_queries:
            start_time = time.time()

            # Run query through workflow with specified model
            output = self._run_workflow(test_case["query"], model_id)
            latency = time.time() - start_time

            # Measure semantic similarity (embedding distance)
            similarity = self._semantic_similarity(output, test_case["expected_output"])

            # Extract cost from metrics
            cost = self._extract_cost_from_metrics(model_id)

            results.append({
                "query": test_case["query"],
                "query_type": test_case["type"],
                "latency": latency,
                "cost": cost,
                "semantic_similarity": similarity,
                "output": output
            })

        return {
            "model_id": model_id,
            "avg_latency": np.mean([r["latency"] for r in results]),
            "total_cost": sum([r["cost"] for r in results]),
            "avg_semantic_similarity": np.mean([r["semantic_similarity"] for r in results]),
            "results": results
        }
```

**Test Query Set** (20 queries):
- 5 simple queries (definition lookups)
- 5 relationship queries (well → curves, curve → well)
- 5 aggregation queries (COUNT, curve counts)
- 5 extraction queries (well name, UWI)

**Evaluation Criteria**:
1. **Cost**: Total tokens × cost-per-token
2. **Latency**: Avg latency per query type
3. **Accuracy**: Semantic similarity to expected outputs (cosine similarity of embeddings)

**Selection Strategy**:
- If model A: cost -20% AND accuracy maintained (≥95% of baseline) → Select A
- If model B: cost same BUT accuracy +10% → Select B
- If model C: cost +10% BUT accuracy +20% → Evaluate cost/accuracy trade-off with user

### 2.2 Per-Use-Case Model Configuration

**Design**: Support different models for different use cases

```python
# services/config/settings.py (additions)
@dataclass(frozen=True)
class Settings:
    # ... existing fields ...

    # Per-use-case model selection
    watsonx_reasoning_model_id: str = "ibm/granite-13b-instruct-v2"
    watsonx_orchestrator_model_id: str = "ibm/granite-3-3-8b-instruct"  # Faster for term extraction
    watsonx_query_expansion_model_id: str = "ibm/granite-3-3-8b-instruct"

    def get_model_for_use_case(self, use_case: str) -> str:
        \"\"\"Get optimal model for specific use case.\"\"\"
        mapping = {
            "reasoning": self.watsonx_reasoning_model_id,
            "orchestrator": self.watsonx_orchestrator_model_id,
            "query_expansion": self.watsonx_query_expansion_model_id,
            "scope_detection": self.watsonx_reasoning_model_id,
        }
        return mapping.get(use_case, self.watsonx_gen_model_id)
```

---

## Phase 3: Prompt Engineering & Optimization (4-5 hours)

### 3.1 Prompt Library Architecture

**Objective**: Centralize prompts with versioning, templates, and easy A/B testing

**Design**:
```
services/prompts/
├── __init__.py
├── templates.py              # Base template classes
├── reasoning_prompts.py      # Reasoning step prompts
├── query_prompts.py          # Query expansion/rewriting
├── scope_prompts.py          # Scope detection
└── orchestrator_prompts.py   # Term extraction
```

**Template System**:
```python
# services/prompts/templates.py
from typing import Dict, Any
from string import Template

class PromptTemplate:
    \"\"\"Base class for prompt templates with variable substitution.\"\"\"

    def __init__(self, template: str, version: str = "v1"):
        self.template = Template(template)
        self.version = version

    def format(self, **kwargs: Any) -> str:
        \"\"\"Substitute variables in template.\"\"\"
        return self.template.safe_substitute(**kwargs)


class ChainOfThoughtPrompt(PromptTemplate):
    \"\"\"Chain-of-thought prompting pattern.\"\"\"

    DEFAULT_TEMPLATE = \"\"\"You are a petroleum engineering expert analyzing data.

Task: $task

Think step-by-step:
1. Understand the query: What is being asked?
2. Identify relevant information: What data do I need?
3. Reason about the answer: How do I combine the information?
4. Generate response: What is the final answer?

Available Context:
$context

Query: $query

Step-by-step reasoning:\"\"\"


class FewShotPrompt(PromptTemplate):
    \"\"\"Few-shot prompting with examples.\"\"\"

    DEFAULT_TEMPLATE = \"\"\"$system_instruction

Examples:

$examples

Now answer this query:
Query: $query
Context: $context
Answer:\"\"\"
```

### 3.2 Reasoning Prompts (Domain-Specific)

**Objective**: Optimize reasoning step prompts with chain-of-thought and petroleum engineering domain knowledge

**Current Prompt** (baseline):
```python
# services/langgraph/workflow.py (current, line ~635)
prompt = f"""Answer the following query using the provided context.

Query: {state.query}

Context:
{context}

Answer:"""
```

**Optimized Prompt** (chain-of-thought + domain-specific):
```python
# services/prompts/reasoning_prompts.py
REASONING_PROMPT_V2 = ChainOfThoughtPrompt(\"\"\"You are a petroleum engineering and geological data expert.

Task: Answer the user's query using ONLY the information provided in the context below. If the answer is not in the context, say "I cannot answer this question with the available data."

Domain Context:
- Well logs contain measurements like GR (gamma ray), NPHI (neutron porosity), RHOB (bulk density)
- Wells are identified by UWI (unique well identifier) or well names
- Curves are measurements taken at different depths in a wellbore

Think step-by-step:
1. What specific information is the query asking for?
2. Which parts of the context contain relevant information?
3. How do I extract and synthesize the answer from the context?
4. Does the context fully answer the question?

Available Context:
$context

User Query: $query

Step-by-step analysis:
1. Query asks for: [identify the specific request]
2. Relevant context sections: [cite specific parts]
3. Extracted information: [pull out facts]
4. Final answer: [synthesize and answer]

Answer (concise, factual, cite sources if possible):\"\"\"
)
```

**Benefits**:
- Chain-of-thought improves reasoning quality
- Domain-specific instructions reduce hallucinations
- Explicit "not in context" handling improves honesty
- Structured output improves parsing reliability

### 3.3 Orchestrator Prompts (Term Extraction)

**Objective**: Improve LocalOrchestrator term extraction accuracy with better prompts

**Current Prompt** (Task 005):
```python
# services/orchestration/local_orchestrator.py:110-122 (current)
prompt = f\"\"\"Extract only the technical term or acronym being asked about. Return ONLY the term, nothing else.

Query: Define porosity in petroleum engineering
Term: porosity

Query: What is GR?
Term: GR

Query: Explain gamma ray logging
Term: gamma ray logging

Query: {query}
Term:\"\"\"
```

**Optimized Prompt** (structured output + more examples):
```python
# services/prompts/orchestrator_prompts.py
TERM_EXTRACTION_PROMPT_V2 = FewShotPrompt(\"\"\"Extract the technical term or acronym being asked about in petroleum engineering queries.

Return ONLY the term in JSON format: {"term": "extracted_term"}

Examples:

Query: Define porosity in petroleum engineering
{"term": "porosity"}

Query: What is GR in well logging?
{"term": "GR"}

Query: Explain gamma ray logging
{"term": "gamma ray logging"}

Query: What does API stand for in oilfield terms?
{"term": "API"}

Query: Tell me about permeability
{"term": "permeability"}

Query: $query
\"\"\"
)
```

**Benefits**:
- JSON output enables reliable parsing (no brittle string matching)
- More examples improve accuracy (5 vs. 3)
- Domain-specific context ("petroleum engineering") primes model

### 3.4 Prompt Parameter Tuning

**Objective**: Find optimal temperature, max_new_tokens, top_p per use case

**Tuning Strategy**:
```python
# scripts/evaluation/prompt_parameter_tuning.py
PARAMETER_GRID = {
    "temperature": [0.0, 0.3, 0.7],
    "max_new_tokens": [128, 256, 512],
    "top_p": [0.9, 1.0]
}

def tune_parameters(use_case: str, test_queries: List[str]):
    best_params = None
    best_score = 0.0

    for temp in PARAMETER_GRID["temperature"]:
        for max_tokens in PARAMETER_GRID["max_new_tokens"]:
            for top_p in PARAMETER_GRID["top_p"]:
                # Run queries with these parameters
                results = evaluate(use_case, test_queries, temp, max_tokens, top_p)

                # Score = weighted combination of accuracy and latency
                score = results["accuracy"] - 0.1 * results["avg_latency"]

                if score > best_score:
                    best_score = score
                    best_params = {"temperature": temp, "max_new_tokens": max_tokens, "top_p": top_p}

    return best_params
```

**Expected Optimal Parameters**:
- **Reasoning/Generation**: temperature=0.0 (deterministic), max_new_tokens=256
- **Orchestrator**: temperature=0.0 (deterministic), max_new_tokens=50 (concise)
- **Query Expansion**: temperature=0.3 (slight creativity), max_new_tokens=128

---

## Phase 4: LocalOrchestrator Production Hardening (2-3 hours)

### 4.1 Error Handling & Retry Logic

**Objective**: Graceful handling of LLM failures, timeouts, and invalid inputs

**Design**:
```python
# services/orchestration/local_orchestrator.py (enhanced)
from services.graph_index.retry_utils import retry_with_backoff

class LocalOrchestrator:

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def extract_term(self, query: str) -> Optional[str]:
        \"\"\"Extract term with retry logic for transient failures.

        Raises:
            RuntimeError: If LLM call fails after retries
            TimeoutError: If LLM call exceeds timeout
        \"\"\"
        try:
            # Add timeout to LLM call
            response = self._call_llm_with_timeout(query, timeout=10.0)

            # Parse JSON response
            try:
                parsed = json.loads(response)
                term = parsed.get("term")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response: {response}, falling back to text parsing")
                term = response.strip()

            # Validate term
            if not self._validate_term(term):
                logger.warning(f"Invalid term extracted: '{term}'")
                return None

            return term

        except TimeoutError:
            logger.error(f"LLM term extraction timed out for query: '{query}'")
            metrics_collector.log_metric("orchestrator", "timeout", 1.0, {"query": query})
            return None

        except Exception as e:
            logger.error(f"Unexpected error in term extraction: {e}")
            metrics_collector.log_metric("orchestrator", "error", 1.0, {"error": str(e)})
            return None

    def _validate_term(self, term: str) -> bool:
        \"\"\"Validate extracted term.

        Returns:
            True if term is valid (1-5 words, alphanumeric + spaces/hyphens)
        \"\"\"
        if not term:
            return False

        # Length check
        if len(term.split()) > 5:
            return False

        # Character check (allow alphanumeric, spaces, hyphens, slashes)
        if not re.match(r'^[a-zA-Z0-9\\s\\-/]+$', term):
            return False

        return True

    def invoke(self, query: str, context: str = "") -> Dict[str, Any]:
        \"\"\"Main orchestrator entry point with comprehensive error handling.\"\"\"

        metadata = {
            "mcp_tool_invoked": False,
            "tool_calls": [],
            "orchestrator_used": True,
            "glossary_query_detected": False,
            "term_extracted": None,
            "orchestrator_error": None
        }

        try:
            # Step 1: Detect glossary query
            if not self.is_glossary_query(query):
                metadata["glossary_query_detected"] = False
                return {"response": "", "metadata": metadata}

            metadata["glossary_query_detected"] = True

            # Step 2: Extract term (with retry logic)
            term = self.extract_term(query)
            metadata["term_extracted"] = term

            if not term:
                # Extraction failed; fall back to direct LLM
                return {"response": "", "metadata": metadata}

            # Step 3: Invoke glossary tool
            tool_result = self.invoke_glossary_tool(term)

            metadata["mcp_tool_invoked"] = True
            metadata["tool_calls"] = ["get_dynamic_definition"]

            # Step 4: Format response
            response = self.format_glossary_response(tool_result)

            return {
                "response": response,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Orchestrator error for query '{query}': {e}")
            metadata["orchestrator_error"] = str(e)

            # Graceful fallback: return empty response (workflow will use direct LLM)
            return {
                "response": "",
                "metadata": metadata
            }
```

### 4.2 Telemetry Integration

**Objective**: Log all orchestrator operations for monitoring

(See Phase 1.4 above for telemetry design)

### 4.3 Unit Tests for Error Handling

**Objective**: Test edge cases and error conditions

```python
# tests/unit/test_local_orchestrator_errors.py
import pytest
from services.orchestration.local_orchestrator import LocalOrchestrator

def test_orchestrator_handles_timeout():
    \"\"\"Test that orchestrator handles LLM timeout gracefully.\"\"\"
    orchestrator = LocalOrchestrator()

    # Mock LLM to timeout
    with pytest.raises(TimeoutError):
        orchestrator._call_llm_with_timeout("test query", timeout=0.001)

    # Invoke should not crash
    result = orchestrator.invoke("What is porosity?")
    assert result["metadata"]["orchestrator_error"] is not None

def test_orchestrator_validates_terms():
    \"\"\"Test term validation rejects invalid terms.\"\"\"
    orchestrator = LocalOrchestrator()

    assert orchestrator._validate_term("porosity") == True
    assert orchestrator._validate_term("gamma ray logging") == True
    assert orchestrator._validate_term("") == False
    assert orchestrator._validate_term("a very long term with more than five words") == False
    assert orchestrator._validate_term("invalid@term!") == False

def test_orchestrator_handles_json_parse_error():
    \"\"\"Test orchestrator handles malformed JSON response.\"\"\"
    orchestrator = LocalOrchestrator()

    # Mock LLM to return invalid JSON
    # ... test implementation ...
```

---

## Phase 5: Performance Optimization (2-3 hours)

### 5.1 Query Result Caching

**Objective**: Cache LLM responses for repeated queries (LRU cache)

**Design**:
```python
# services/langgraph/workflow.py (additions)
from functools import lru_cache
import hashlib

def _cache_key(query: str, context_hash: str) -> str:
    \"\"\"Generate cache key from query + context hash.\"\"\"
    return hashlib.sha256(f"{query}:{context_hash}".encode()).hexdigest()

@lru_cache(maxsize=100)
def _cached_generation(query: str, context_hash: str, prompt: str) -> str:
    \"\"\"Cached LLM generation (only for deterministic queries).\"\"\"
    gen_client = get_generation_client()
    return gen_client.generate(prompt, temperature=0.0, max_new_tokens=256)

def _generate_llm_response(state: WorkflowState) -> None:
    \"\"\"Generate LLM response with caching.\"\"\"
    context_hash = hashlib.sha256(state.retrieved.encode()).hexdigest()[:16]
    cache_key = _cache_key(state.query, context_hash)

    # Try cache first
    try:
        cached_response = _cached_generation(state.query, context_hash, prompt)
        state.response = cached_response
        state.metadata["cache_hit"] = True
        metrics_collector.log_metric("cache", "hit", 1.0, {"query": state.query})
        return
    except:
        # Cache miss, generate normally
        state.metadata["cache_hit"] = False
        metrics_collector.log_metric("cache", "miss", 1.0, {"query": state.query})
```

**Benefits**:
- Reduces latency for repeated queries from ~5s to <100ms
- Reduces cost (no LLM API call for cached queries)
- LRU eviction prevents unbounded memory growth

### 5.2 Async Glossary Fetching (Stretch Goal)

**Objective**: Fetch glossary definitions in parallel using asyncio

**Design** (simplified):
```python
# services/mcp/glossary_scraper.py (async version)
import asyncio
import aiohttp

class AsyncGlossaryScraper:
    async def scrape_async(self, term: str) -> Definition:
        \"\"\"Async scraping from multiple sources in parallel.\"\"\"

        tasks = [
            self._scrape_slb_async(term),
            self._scrape_spe_async(term),
            # ... other sources ...
        ]

        # Wait for first successful result (race)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result is not None:
                return result

        return self._fallback_static_definition(term)
```

**Note**: This is a stretch goal - only implement if time permits. Synchronous version with rate limiting is adequate.

---

## Phase 6: Security & Dependency Updates (1 hour)

**Objective**: Upgrade pip (if available) and audit dependencies

**Tasks**:
1. Check pip version: `pip --version`
2. Upgrade if pip 25.3 available: `pip install --upgrade pip`
3. Run pip-audit: `pip-audit --desc`
4. Update deprecated packages (if any)
5. Lock versions in requirements.txt

---

## Phase 7: Testing & Validation (2-3 hours)

### 7.1 Test Execution

**E2E Tests** (Hard Requirement):
```bash
pytest tests/critical_path/test_cp_workflow_e2e.py -v
# Expected: 19/20 pass (95%), same as Task 006
```

**LocalOrchestrator Tests**:
```bash
pytest tests/unit/test_local_orchestrator*.py -v --cov=services.orchestration --cov-report=term
# Expected: ≥90% branch coverage
```

**Deferred Tests** (Task 002):
```bash
pytest tests/validation/test_glossary_authenticity.py -m authenticity -v
# Authenticity tests for glossary scraper
```

### 7.2 Statistical Validation

**Latency Improvement** (Paired t-test):
```python
# scripts/evaluation/statistical_validation.py
from scipy import stats

def validate_latency_improvement(before: List[float], after: List[float]):
    \"\"\"Paired t-test for latency improvement.\"\"\"
    t_stat, p_value = stats.ttest_rel(before, after)

    improvement = (np.mean(before) - np.mean(after)) / np.mean(before) * 100

    print(f"Latency Improvement: {improvement:.1f}%")
    print(f"p-value: {p_value:.4f}")
    print(f"Significant at α=0.05: {p_value < 0.05}")

    assert p_value < 0.05, "Latency improvement not statistically significant"
    assert improvement >= 40, f"Latency improvement {improvement}% < target 40%"
```

**Cost Reduction** (Paired t-test):
```python
def validate_cost_reduction(before_cost: List[float], after_cost: List[float]):
    \"\"\"Paired t-test for cost reduction.\"\"\"
    # Similar to latency validation
```

**LocalOrchestrator Accuracy** (Binomial test):
```python
def validate_orchestrator_accuracy(successes: int, trials: int):
    \"\"\"Binomial test for term extraction accuracy ≥90%.\"\"\"
    p_value = stats.binom_test(successes, trials, p=0.9, alternative='greater')

    accuracy = successes / trials * 100

    print(f"Term Extraction Accuracy: {accuracy:.1f}%")
    print(f"p-value: {p_value:.4f}")

    assert accuracy >= 90, f"Accuracy {accuracy}% < target 90%"
```

### 7.3 Validation Report Generation

**Objective**: Create comprehensive VALIDATION_REPORT.md documenting all metrics

(Similar structure to Task 006 VALIDATION_REPORT.md)

---

## Git Commit Strategy

**Incremental Commits** (per phase):
1. Phase 1 commit: "feat: Add monitoring infrastructure (Task 007 Phase 1)"
2. Phase 2 commit: "feat: Add model evaluation framework (Task 007 Phase 2)"
3. Phase 3 commit: "feat: Add prompt library and optimization (Task 007 Phase 3)"
4. Phase 4 commit: "feat: Harden LocalOrchestrator for production (Task 007 Phase 4)"
5. Phase 5 commit: "feat: Add performance optimizations (Task 007 Phase 5)"
6. Final commit: "docs: Add Task 007 validation report"

**All commits include**:
- Updated tests
- Updated documentation
- Decision log entry

---

## Success Criteria (Recap)

✅ **All 5 metrics achieved** (see hypothesis.md)
✅ **E2E test pass rate ≥95%** (19/20)
✅ **All HIGH priority limitations remediated** (10/15)
✅ **VALIDATION_REPORT.md complete** with before/after comparisons

---

**Next File**: evidence.json
