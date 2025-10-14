# Glossary - Task 007

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14

---

## Monitoring & Observability

### Latency
**Definition**: Time elapsed between query submission and response completion, measured in seconds or milliseconds.

**Context**: Task 007 tracks latency per workflow step (embedding, retrieval, reasoning, generation) to identify bottlenecks.

**Measurement**: P50 (median), P95 (95th percentile), P99 (99th percentile) latencies are standard metrics.

**Example**: "P95 latency <3s" means 95% of queries complete in under 3 seconds.

**Related Terms**: Throughput, Response Time, QoS (Quality of Service)

---

### P95 Latency
**Definition**: The 95th percentile latency; 95% of queries complete faster than this threshold, 5% are slower.

**Context**: Task 007 targets P95 latency reduction from ~5s to <3s (40% improvement).

**Why P95**: Balances typical performance (not median, which ignores outliers) with worst-case (not P99, which is too sensitive to rare outliers).

**Calculation**: Sort latencies ascending, select value at position 0.95 × n.

**Related Terms**: P50 (median), P99, SLA (Service Level Agreement)

---

### MELT Framework
**Definition**: Metrics, Events, Logs, Traces - four pillars of observability for distributed systems.

**Context**: Task 007 implements MELT-inspired design:
- **Metrics**: Latency, cost, cache hit rate (numeric aggregates)
- **Events**: Orchestrator invocation, fallback events (discrete occurrences)
- **Logs**: Structured JSON logs per metric type
- **Traces**: Not implemented (would require distributed tracing framework)

**Source**: E-007-004 (OpenTelemetry)

**Related Terms**: Observability, Telemetry, Instrumentation

---

### Instrumentation
**Definition**: Adding code to measure and log system behavior (latency, cost, errors) without changing functional logic.

**Context**: Task 007 Phase 1 adds instrumentation to workflow.py, generation.py, local_orchestrator.py.

**Best Practice**: Instrumentation overhead should be <1% of total operation time (<5ms for 5s query).

**Pattern**: Context managers (`with LatencyTracker(...):`) and decorators (`@log_cost`) are common instrumentation patterns.

**Related Terms**: Observability, Telemetry, Profiling

---

### Telemetry
**Definition**: Automated collection and transmission of measurements from remote or inaccessible systems.

**Context**: LocalOrchestrator telemetry tracks invocation rate, success rate, fallback rate, term extraction latency.

**Format**: Structured JSON logs with timestamp, metric_type, metric_name, value, metadata.

**Related Terms**: Instrumentation, Observability, Monitoring

---

## Prompt Engineering

### Chain-of-Thought (CoT) Prompting
**Definition**: Prompting technique that guides LLM to generate step-by-step reasoning before producing final answer.

**Context**: Task 007 adds CoT prompts to reasoning_step (e.g., "Think step-by-step: 1. Understand query, 2. Identify relevant info, 3. Reason about answer").

**Evidence**: E-007-001 shows CoT only yields gains for models ~100B parameters; granite-13b may be too small.

**Pattern**:
```
Think step-by-step:
1. What is the query asking?
2. What information do I need?
3. How do I combine the information?
4. What is the final answer?
```

**Related Terms**: Few-Shot Prompting, Zero-Shot CoT, Reasoning

---

### Few-Shot Prompting
**Definition**: Providing 2-5 examples of (input, expected output) pairs in prompt to guide LLM behavior.

**Context**: Task 007 uses few-shot prompting for LocalOrchestrator term extraction (5 examples of query → extracted term).

**Evidence**: E-007-005 shows few-shot prompting helps LLMs structure outputs correctly.

**Pattern**:
```
Examples:
Query: "What is porosity?"
Term: "porosity"

Query: "Define GR in well logging"
Term: "GR"

Your turn:
Query: "Explain gamma ray logging"
Term: ?
```

**Related Terms**: Zero-Shot Prompting, Chain-of-Thought, In-Context Learning

---

### Structured Output
**Definition**: Requesting LLM to produce output in specific format (JSON, XML, CSV) rather than unstructured text.

**Context**: Task 007 prompts LocalOrchestrator to return `{"term": "extracted_term"}` JSON instead of free text.

**Benefits**: Easier parsing, fewer errors, validation via JSON schema.

**Pattern**:
```
Return ONLY valid JSON in this format:
{"term": "extracted_term"}

Do not include any other text.
```

**Related Terms**: JSON Mode, Constrained Decoding, Output Parsing

---

### Prompt Template
**Definition**: Reusable string template with placeholders for dynamic values, used to generate prompts programmatically.

**Context**: Task 007 creates prompt library (services/prompts/) with versioned templates (REASONING_PROMPT_V1, REASONING_PROMPT_V2).

**Pattern**: Python `string.Template` with `$variable` placeholders.

**Example**:
```python
template = Template("Query: $query\nContext: $context")
prompt = template.safe_substitute(query="What is porosity?", context="...")
```

**Related Terms**: Prompt Engineering, Jinja2 Templates, String Interpolation

---

### Semantic Similarity
**Definition**: Measure of how similar two texts are in meaning, typically computed as cosine similarity of embeddings.

**Context**: Task 007 measures semantic similarity between LLM outputs before/after prompt optimization (target: ≥15% improvement).

**Calculation**:
```python
from sklearn.metrics.pairwise import cosine_similarity
sim = cosine_similarity([embedding1], [embedding2])[0][0]  # range: -1 to 1
```

**Interpretation**: >0.9 = very similar, 0.7-0.9 = similar, 0.5-0.7 = somewhat similar, <0.5 = dissimilar.

**Related Terms**: Embedding, Cosine Similarity, Semantic Search

---

## LLM & Machine Learning

### LLM (Large Language Model)
**Definition**: Neural network trained on massive text corpora to generate human-like text, typically with billions of parameters.

**Context**: Task 007 evaluates granite-13b-instruct-v2 (13 billion parameters, deprecated) vs granite-3-3-8b-instruct (3.3 billion parameters, newer).

**Key Properties**:
- **Temperature**: Controls randomness (0.0 = deterministic, 1.0 = creative)
- **Top-p (nucleus sampling)**: Controls diversity of token selection
- **Max new tokens**: Limits output length

**Related Terms**: Transformer, GPT, Granite, Foundation Model

---

### Granite Models
**Definition**: IBM's family of open-source LLMs trained on enterprise and code data.

**Context**: Task 007 uses granite models via watsonx.ai API:
- `ibm/granite-13b-instruct-v2`: 13B parameters, instruction-tuned, deprecated
- `ibm/granite-3-3-8b-instruct`: 3.3B parameters, instruction-tuned, recommended
- `ibm/granite-13b-chat-v2`: 13B parameters, conversational variant

**Source**: IBM watsonx.ai model catalog

**Related Terms**: Foundation Model, Instruction Tuning, LLM

---

### Temperature
**Definition**: LLM parameter controlling output randomness; 0.0 = deterministic (greedy decoding), 1.0+ = creative/random.

**Context**: Task 007 uses temperature=0.0 for deterministic outputs (enables caching, reproducibility).

**Typical Values**:
- 0.0: Factual Q&A, code generation (deterministic)
- 0.3-0.7: Chatbots, creative writing (balanced)
- 1.0+: Poetry, brainstorming (highly creative)

**Related Terms**: Top-p, Sampling, Greedy Decoding

---

### Embedding
**Definition**: Dense vector representation of text (typically 768-1536 dimensions) capturing semantic meaning.

**Context**: Task 007 uses `ibm/granite-embedding-278m-multilingual` to embed queries and documents for retrieval.

**Usage**: Cosine similarity between embeddings measures semantic similarity.

**Model**: granite-embedding-278m (278 million parameters, 768 dimensions).

**Related Terms**: Vector Search, Semantic Similarity, AstraDB

---

### Token
**Definition**: Smallest unit of text processed by LLM; typically a word, subword, or punctuation mark.

**Context**: Task 007 tracks input_tokens and output_tokens per LLM API call for cost estimation.

**Tokenization**: "Hello, world!" → ["Hello", ",", " world", "!"] (4 tokens, typical)

**Cost**: Watsonx.ai charges per 1000 tokens (~$0.001-0.002 per 1K tokens for granite models).

**Related Terms**: Tokenizer, BPE (Byte Pair Encoding), Cost Tracking

---

## Performance Optimization

### Caching
**Definition**: Storing results of expensive operations (LLM API calls, embeddings) for reuse on repeated inputs.

**Context**: Task 007 implements two caching layers:
1. **Redis cache**: Embedding cache (already implemented in Task 002)
2. **LRU cache**: Query result cache (new in Task 007 Phase 5)

**Benefits**: Reduces latency, reduces cost (fewer LLM API calls), improves user experience.

**Related Terms**: LRU Cache, Redis, Cache Hit Rate

---

### LRU Cache (Least Recently Used)
**Definition**: Cache eviction policy that removes least recently accessed items when cache is full.

**Context**: Task 007 uses `@lru_cache(maxsize=100)` for query result caching.

**Rationale**: LRU prioritizes frequently accessed items (hot queries) over infrequently accessed items (cold queries).

**Implementation**: Python `functools.lru_cache` provides built-in LRU cache with O(1) lookup.

**Related Terms**: Caching, Eviction Policy, Cache Hit Rate

---

### Cache Hit Rate
**Definition**: Percentage of cache lookups that find requested item in cache (vs. cache miss, requiring recomputation).

**Context**: Task 007 targets ≥60% cache hit rate for query result caching.

**Calculation**: `cache_hit_rate = cache_hits / (cache_hits + cache_misses)`

**Typical Values**:
- <40%: Poor (cache too small or queries too diverse)
- 40-70%: Good (acceptable hit rate)
- >70%: Excellent (high benefit from caching)

**Related Terms**: Cache Miss, Caching, LRU Cache

---

### Retry Logic
**Definition**: Automatically retrying failed operations (API calls, database queries) before reporting error to user.

**Context**: Task 007 reuses retry logic from Task 006 (exponential backoff: 1s, 2s, 4s delays).

**Pattern**: Retry only transient errors (HTTP 429 rate limit, 500 server error, network timeouts), not permanent errors (HTTP 400 bad request, 404 not found).

**Implementation**: Decorator pattern `@retry_with_backoff(max_retries=3)`.

**Related Terms**: Exponential Backoff, Resilience, Error Handling

---

### Exponential Backoff
**Definition**: Retry strategy where delay between retries increases exponentially (1s, 2s, 4s, 8s, ...).

**Context**: Task 006 implemented exponential backoff for AstraDB and WatsonX clients; Task 007 reuses for LocalOrchestrator.

**Rationale**: Reduces load on failing service (prevents thundering herd), gives service time to recover.

**Formula**: `delay = base_delay × 2^(attempt - 1)` (e.g., base_delay=1s → 1s, 2s, 4s, 8s)

**Related Terms**: Retry Logic, Circuit Breaker, Rate Limiting

---

## Statistical Validation

### Paired t-Test
**Definition**: Statistical test comparing means of two related samples (before/after measurements on same subjects).

**Context**: Task 007 uses paired t-test for latency, cost, and semantic similarity comparisons (before/after optimization on same 20 queries).

**Rationale**: Paired design controls for query difficulty (each query is its own control), increasing statistical power vs. independent samples t-test.

**Requirements**:
- Normality: Differences should be approximately normally distributed (Shapiro-Wilk test)
- Independence: Each pair should be independent of other pairs

**Null Hypothesis (H0)**: Mean difference = 0 (no improvement)
**Alternative (H1)**: Mean difference ≠ 0 (improvement or regression)

**Related Terms**: Statistical Significance, p-value, Effect Size

---

### Statistical Significance (α)
**Definition**: Probability of rejecting null hypothesis when it is true (Type I error rate); conventionally set to α=0.05 (5%).

**Context**: Task 007 uses α=0.05; p-value <0.05 indicates statistically significant improvement.

**Interpretation**:
- p < 0.05: Reject H0, conclude improvement is real (not due to chance)
- p ≥ 0.05: Fail to reject H0, cannot conclude improvement (may be due to chance)

**Related Terms**: p-value, Type I Error, Type II Error, Statistical Power

---

### Effect Size
**Definition**: Standardized measure of magnitude of difference between two groups (Cohen's d for t-tests).

**Context**: Task 007 reports effect sizes (Cohen's d) even if p-value is not significant; large effect (d>0.8) is meaningful regardless of p-value.

**Calculation (Cohen's d)**: `d = (mean1 - mean2) / pooled_std`

**Interpretation**:
- d < 0.2: Small effect
- 0.2 ≤ d < 0.5: Medium effect
- 0.5 ≤ d < 0.8: Large effect
- d ≥ 0.8: Very large effect

**Related Terms**: Statistical Significance, Statistical Power, Practical Significance

---

### Statistical Power
**Definition**: Probability of correctly rejecting null hypothesis when alternative is true (1 - Type II error rate); conventionally set to power ≥0.80 (80%).

**Context**: Task 007 requires power ≥0.80 for paired t-tests; n=20 provides adequate power for large effect sizes (40% latency improvement).

**Power Analysis**: Calculate required sample size before experiment to ensure adequate power:
```python
from statsmodels.stats.power import ttest_power
power = ttest_power(effect_size=0.8, nobs=20, alpha=0.05)  # paired design
```

**Trade-offs**:
- Larger n → higher power (easier to detect small effects)
- Larger effect size → higher power (easier to detect with small n)

**Related Terms**: Type II Error, Sample Size, Effect Size

---

### Binomial Test
**Definition**: Statistical test for binary outcomes (success/failure) comparing observed success rate to expected rate.

**Context**: Task 007 uses binomial test for LocalOrchestrator term extraction accuracy (H0: accuracy ≤90%, H1: accuracy >90%, n=20 queries).

**Example**: If 18/20 term extractions succeed, is this significantly >90%?
```python
from scipy.stats import binom_test
p_value = binom_test(18, 20, 0.90, alternative='greater')  # one-sided test
```

**Related Terms**: Proportion Test, Chi-Square Test, Statistical Significance

---

## Orchestration

### LocalOrchestrator
**Definition**: Custom proof-of-concept orchestrator for MCP (Model Context Protocol) tool calling with watsonx.ai, implemented in Task 005.

**Context**: Task 007 hardens LocalOrchestrator for production (error handling, retry logic, timeout handling, telemetry).

**Current State**: 121 NLOC, max CCN=5, 100% tool invocation on 5 test cases (proof-of-concept).

**Target State**: ~200-300 NLOC, production-grade with ≥90% term extraction accuracy on 20 test cases.

**Related Terms**: MCP, watsonx.orchestrate, Agentic Workflows

---

### MCP (Model Context Protocol)
**Definition**: Protocol for connecting LLMs to external tools (APIs, databases, functions) via structured function calling.

**Context**: LocalOrchestrator uses MCP to call glossary definition tool when query is out-of-scope (e.g., "What is ROI?").

**Pattern**: LLM generates JSON function call → orchestrator executes function → result returned to LLM.

**Related Terms**: Function Calling, Tool Use, Agentic Workflows

---

### watsonx.orchestrate
**Definition**: IBM's enterprise orchestration framework for AI workflows, integrating LLMs, automation, and business processes.

**Context**: Task 006 identified orchestrate migration as known limitation; Task 007 defers migration per user preference.

**Status**: Not yet available on user's watsonx.ai instance (ADR-006-008).

**Alternative**: LocalOrchestrator (simple, composable, validated by Anthropic best practices).

**Related Terms**: LocalOrchestrator, MCP, Agentic Workflows

---

## General Terms

### Metric
**Definition**: Quantitative measure of system property (latency, cost, accuracy) used for performance evaluation.

**Context**: Task 007 defines 5 metrics:
1. Performance (P95 latency)
2. Cost (LLM API cost)
3. LocalOrchestrator (term extraction accuracy)
4. Prompts (semantic similarity)
5. Observability (instrumentation coverage)

**Related Terms**: KPI (Key Performance Indicator), SLA, Baseline

---

### Baseline
**Definition**: Initial measurement before optimization, used as reference point for comparison.

**Context**: Task 007 establishes baselines:
- P95 latency: ~5s (current)
- Test pass rate: 19/20 (95%)
- Cost: No tracking (to be measured)

**Related Terms**: Before/After, Control, Benchmark

---

### Regression
**Definition**: Introduction of new bug or performance degradation in previously working functionality.

**Context**: Task 007 monitors for regressions via E2E test pass rate (must maintain ≥95%); prompt optimization may cause regressions.

**Types**:
- **Functional regression**: Tests that previously passed now fail
- **Performance regression**: Latency or cost increases
- **Accuracy regression**: LLM output quality decreases

**Related Terms**: Quality Assurance, Test Suite, Rollback

---

## Acronyms

| Acronym | Full Form | Definition |
|---------|-----------|------------|
| CCN | Cyclomatic Complexity Number | Code complexity metric (Task 006 target: ≤10) |
| CoT | Chain-of-Thought | Prompting technique for step-by-step reasoning |
| E2E | End-to-End | Full workflow testing (query → response) |
| LLM | Large Language Model | Billion-parameter neural network for text generation |
| LRU | Least Recently Used | Cache eviction policy |
| MCP | Model Context Protocol | Protocol for LLM tool calling |
| MELT | Metrics, Events, Logs, Traces | Observability framework |
| NLOC | Non-Comment Lines of Code | Code size metric (excludes comments, blank lines) |
| P50 | 50th Percentile | Median latency |
| P95 | 95th Percentile | 95% of queries complete faster than this |
| P99 | 99th Percentile | 99% of queries complete faster than this |
| QA | Quality Assurance | Testing and validation process |
| SLA | Service Level Agreement | Committed performance thresholds |
| TTL | Time To Live | Cache entry expiration time |

---

**Last Updated**: 2025-10-14
**Next File**: executive_summary.md
