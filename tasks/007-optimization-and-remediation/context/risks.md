# Risk Assessment - Task 007

**Task ID**: 007-optimization-and-remediation
**Protocol**: SCA v9-Compact
**Date**: 2025-10-14

---

## Risk Matrix

| Risk ID | Risk | Likelihood | Impact | Severity | Mitigation Status |
|---------|------|------------|--------|----------|-------------------|
| RISK-007-001 | Model unavailability | Medium | Medium | 🟡 Medium | Planned |
| RISK-007-002 | Prompt optimization regression | Medium | High | 🔴 High | Planned |
| RISK-007-003 | Instrumentation overhead | Low | Medium | 🟢 Low | Planned |
| RISK-007-004 | Cost increase from experimentation | Low | Low | 🟢 Low | Planned |
| RISK-007-005 | Time overrun | Medium | Medium | 🟡 Medium | Planned |
| RISK-007-006 | Statistical test insufficient power | Low | High | 🟡 Medium | Planned |
| RISK-007-007 | Cache invalidation bugs | Medium | Medium | 🟡 Medium | Planned |
| RISK-007-008 | Async refactoring complexity | Medium | Low | 🟢 Low | Planned |
| RISK-007-009 | LocalOrchestrator accuracy regression | Low | High | 🟡 Medium | Planned |
| RISK-007-010 | Metrics storage performance | Low | Low | 🟢 Low | Planned |

---

## Detailed Risk Analysis

### RISK-007-001: Model Unavailability

**Description**: granite-3-3-8b-instruct may not be available on current watsonx.ai instance, blocking model benchmarking (Phase 2).

**Likelihood**: Medium (30-50%)
- Newer model, may not be deployed to all watsonx.ai instances
- API documentation may be outdated

**Impact**: Medium
- Blocks Metric 2 (cost optimization) validation
- Fallback to granite-13b-chat-v2 may have different characteristics
- Model selection decision delayed or suboptimal

**Mitigation Strategies**:
1. **Early validation**: Check model availability via API before starting Phase 2
   ```python
   # Test API call to verify model exists
   response = client.generate("test prompt", model_id="ibm/granite-3-3-8b-instruct")
   ```
2. **Fallback models**: Document alternative models if granite-3-3-8b unavailable:
   - granite-13b-chat-v2 (conversational variant)
   - mixtral-8x7b-instruct-v01 (if available)
3. **Document limitations**: If no alternative model available, document evaluation as incomplete and defer to future task

**Residual Risk**: Low (after mitigation)
- Fallback models provide alternative benchmarking path
- Documentation ensures transparency

**Monitoring**: API error logs during model benchmarking

---

### RISK-007-002: Prompt Optimization Regression

**Description**: New prompts (chain-of-thought, few-shot) may break existing test cases or reduce accuracy, causing E2E test pass rate to drop below 95% threshold.

**Likelihood**: Medium (30-50%)
- Prompts are highly sensitive to wording changes
- Chain-of-thought may increase verbosity, cause timeout issues
- LLM behavior is non-deterministic

**Impact**: High
- Blocks Task 007 completion (hard requirement: ≥95% pass rate)
- May require multiple prompt iteration cycles
- User-facing functionality degraded

**Mitigation Strategies**:
1. **Incremental validation**: Test new prompts on subset of queries before full E2E suite
   ```python
   # Test new reasoning prompt on 5 simple queries first
   test_queries = ["What is porosity?", "What is permeability?", ...]
   for query in test_queries:
       validate_response(query, new_reasoning_prompt)
   ```
2. **Maintain baseline prompts**: Keep original prompts in code (versioned) for rollback
   ```python
   REASONING_PROMPT_V1 = "..."  # Original (baseline)
   REASONING_PROMPT_V2 = "..."  # Optimized (new)
   ```
3. **Semantic similarity check**: Measure cosine similarity between baseline and new prompt outputs
   - Alert if similarity <80% (indicates significant behavior change)
4. **Manual review**: Inspect 10 LLM responses before/after prompt changes

**Residual Risk**: Medium (after mitigation)
- Prompt optimization inherently risky
- Mitigation reduces but doesn't eliminate regression risk

**Monitoring**: E2E test pass rate after each prompt change; semantic similarity scores

---

### RISK-007-003: Instrumentation Overhead

**Description**: Metrics collection (latency tracking, cost tracking) adds >5ms overhead per query, negating performance improvements.

**Likelihood**: Low (10-30%)
- Context managers and decorators are lightweight
- File I/O is async and non-blocking

**Impact**: Medium
- Metric 1 (P95 latency improvement) invalidated if instrumentation adds overhead
- User-facing latency increase

**Mitigation Strategies**:
1. **Async file writing**: Use queue + background thread for metrics logging
   ```python
   class MetricsCollector:
       def __init__(self):
           self.queue = Queue()
           self.writer_thread = Thread(target=self._write_loop, daemon=True)
           self.writer_thread.start()
   ```
2. **Measure overhead**: Run test queries with/without instrumentation, measure difference
3. **Conditional instrumentation**: Disable metrics in production if overhead exceeds 5ms threshold
   ```python
   if settings.metrics_enabled and overhead < 5.0:
       with LatencyTracker(...):
           ...
   ```

**Residual Risk**: Low (after mitigation)
- Async I/O makes overhead negligible
- Conditional disable provides safety valve

**Monitoring**: Instrumentation overhead logged as separate metric

---

### RISK-007-004: Cost Increase from Experimentation

**Description**: Model benchmarking (20 queries × 2 models) and prompt testing incur LLM API costs beyond normal usage.

**Likelihood**: Low (10-30%)
- API calls are metered, costs are predictable
- watsonx.ai pricing is documented

**Impact**: Low
- Estimated cost: ~$10-20 for benchmarking (40 LLM API calls)
- Within project budget

**Mitigation Strategies**:
1. **Budget allocation**: Reserve $50 for Task 007 experimentation
2. **Cost tracking**: Log all API calls during benchmarking to cost_metrics.json
3. **Minimize redundant calls**: Cache embedding results, reuse when possible

**Residual Risk**: Low (after mitigation)
- Costs are bounded and budgeted

**Monitoring**: cost_metrics.json aggregated after each phase

---

### RISK-007-005: Time Overrun

**Description**: Task 007 estimate (17-22 hours) may be insufficient if multiple phases require iteration (prompt regression fixes, model unavailability).

**Likelihood**: Medium (30-50%)
- Complex task with 7 phases
- Prompt optimization is inherently iterative
- Model availability unknown

**Impact**: Medium
- Delays downstream tasks
- May require scope reduction (defer MEDIUM priority items)

**Mitigation Strategies**:
1. **Prioritize HIGH priority phases**: Focus on Phases 1-4, defer Phase 5/6 if needed
   - HIGH: Instrumentation (Phase 1), Model Selection (Phase 2), Prompts (Phase 3), LocalOrchestrator (Phase 4)
   - MEDIUM: Performance Optimization (Phase 5), Security Updates (Phase 6)
2. **Timebox phases**: Set 3-hour limit per phase; document incomplete work and move on
3. **Checkpoint commits**: Commit after each phase to preserve progress

**Residual Risk**: Medium (after mitigation)
- Iteration cycles are unpredictable
- Prioritization ensures core objectives achieved

**Monitoring**: Time tracking per phase; alert if >3 hours spent on single phase

---

### RISK-007-006: Statistical Test Insufficient Power

**Description**: n=20 test queries may provide insufficient statistical power to detect 40% latency improvement or 20% cost reduction (α=0.05, power=0.80 target).

**Likelihood**: Low (10-30%)
- Effect sizes are large (40%, 20%), easier to detect
- Paired design increases power

**Impact**: High
- Cannot statistically validate hypothesis metrics
- Results not scientifically rigorous

**Mitigation Strategies**:
1. **Power analysis**: Calculate required sample size before starting validation
   - For 40% effect size, paired t-test, α=0.05, power=0.80: n≈15-20 (adequate)
2. **Increase n if needed**: Add more test queries if power analysis shows n=20 insufficient
3. **Effect size reporting**: Report effect sizes (Cohen's d) even if p-value not significant
   - Large effect size (d>0.8) is meaningful even if p>0.05

**Residual Risk**: Low (after mitigation)
- Large effect sizes are detectable with n=20
- Effect size reporting provides interpretability

**Monitoring**: Power analysis results documented in VALIDATION_REPORT.md

---

### RISK-007-007: Cache Invalidation Bugs

**Description**: LRU cache key (query, context_hash, prompt) may not capture all factors affecting output, causing stale cache hits.

**Likelihood**: Medium (30-50%)
- LLM generation has non-deterministic parameters (temperature, top_p)
- Context may change even if hash is same (rare but possible)

**Impact**: Medium
- Incorrect query responses served from cache
- User-facing accuracy degradation
- Hard to debug (cache hit is silent)

**Mitigation Strategies**:
1. **Comprehensive cache key**: Include temperature, max_new_tokens in cache key
   ```python
   cache_key = (query, context_hash, prompt, temperature, max_new_tokens)
   ```
2. **Cache TTL**: Add time-based expiration (e.g., 1 hour TTL) to prevent long-lived stale entries
3. **Cache validation**: Log cache hits with metadata; manually inspect for staleness
4. **Disable cache in tests**: E2E tests should disable cache to ensure functional correctness

**Residual Risk**: Medium (after mitigation)
- Cache invalidation is inherently complex
- Logging and TTL reduce risk but don't eliminate it

**Monitoring**: Cache hit logs with query/response pairs; manual inspection for staleness

---

### RISK-007-008: Async Refactoring Complexity

**Description**: Making glossary scraper async (Phase 5 stretch goal) may introduce concurrency bugs, race conditions.

**Likelihood**: Medium (30-50%)
- Async programming is error-prone
- Glossary scraper has rate limiting, robots.txt logic

**Impact**: Low
- Async glossary is stretch goal, not required for Task 007 success
- Can be deferred to future task if too complex

**Mitigation Strategies**:
1. **Keep sync version**: Do not delete sync glossary scraper; async is opt-in feature
2. **Defer if complex**: If async refactoring takes >2 hours, mark as future work
3. **Async testing**: Use pytest-asyncio to test async glossary scraper in isolation

**Residual Risk**: Low (after mitigation)
- Async glossary is optional
- Sync version remains as fallback

**Monitoring**: Time spent on async refactoring; defer if >2 hours

---

### RISK-007-009: LocalOrchestrator Accuracy Regression

**Description**: Adding retry logic, timeout handling, and error handling may change LocalOrchestrator behavior, reducing term extraction accuracy below 90% target.

**Likelihood**: Low (10-30%)
- Retry logic should preserve behavior (retries same LLM call)
- Timeout handling only adds safety, doesn't change logic

**Impact**: High
- Metric 3 (LocalOrchestrator production readiness) not achieved
- User-facing glossary functionality degraded

**Mitigation Strategies**:
1. **Unit tests for error conditions**: Test timeout, LLM failure, invalid input handling
   ```python
   def test_orchestrator_timeout():
       with pytest.raises(TimeoutError):
           orchestrator.extract_term("test query", timeout=0.001)
   ```
2. **Baseline comparison**: Run orchestrator on same 20 test queries before/after hardening
   - Measure term extraction accuracy (precision/recall)
3. **Manual review**: Inspect orchestrator outputs for 10 queries after hardening

**Residual Risk**: Low (after mitigation)
- Retry logic is idempotent (same LLM call repeated)
- Unit tests catch behavioral changes

**Monitoring**: Term extraction accuracy on test queries; manual review of outputs

---

### RISK-007-010: Metrics Storage Performance

**Description**: Metrics logs (latency, cost, cache, orchestrator) may grow large (>100 MB) over time, causing disk I/O performance issues.

**Likelihood**: Low (10-30%)
- Metrics logs are append-only JSON
- Test runs generate ~50-100 KB per run

**Impact**: Low
- Slower metrics logging (negligible if async)
- Disk space consumption

**Mitigation Strategies**:
1. **Log rotation**: Implement daily log rotation (keep last 7 days)
   ```python
   log_file = f"logs/metrics_latency_{date.today()}.json"
   ```
2. **Retention policy**: Document retention policy (90 days for latency/cost/orchestrator, 30 days for cache)
3. **Compression**: Compress logs older than 7 days (gzip)

**Residual Risk**: Low (after mitigation)
- Log rotation prevents unbounded growth
- 90-day retention provides adequate historical data

**Monitoring**: Disk space usage in logs/ directory

---

## Risk Prioritization

**Critical Risks** (require immediate mitigation before starting phases):
1. RISK-007-002 (Prompt optimization regression) - HIGH impact
   - **Action**: Create risk_007_002_prompt_validation.md with validation checklist

**High Risks** (monitor closely during execution):
2. RISK-007-005 (Time overrun) - MEDIUM impact, MEDIUM likelihood
   - **Action**: Set 3-hour timebox per phase
3. RISK-007-007 (Cache invalidation bugs) - MEDIUM impact, MEDIUM likelihood
   - **Action**: Comprehensive cache key design

**Medium/Low Risks** (standard mitigations):
4. All other risks - standard mitigations documented above

---

## Risk Monitoring Plan

| Phase | Risks to Monitor | Monitoring Frequency |
|-------|------------------|----------------------|
| Phase 0 (Context) | RISK-007-005 (time) | Daily |
| Phase 1 (Instrumentation) | RISK-007-003 (overhead), RISK-007-010 (storage) | After phase |
| Phase 2 (Model Selection) | RISK-007-001 (model unavailability), RISK-007-004 (cost) | Before phase start |
| Phase 3 (Prompts) | RISK-007-002 (prompt regression) | After each prompt change |
| Phase 4 (LocalOrchestrator) | RISK-007-009 (accuracy regression) | After phase |
| Phase 5 (Performance) | RISK-007-007 (cache bugs), RISK-007-008 (async complexity) | After phase |
| Phase 7 (Validation) | RISK-007-006 (statistical power) | Before statistical tests |

---

## Contingency Plans

**If RISK-007-001 occurs (model unavailability)**:
- Fallback to granite-13b-chat-v2 benchmarking
- Document evaluation as incomplete, defer optimal model selection to Task 008

**If RISK-007-002 occurs (prompt regression)**:
- Rollback to baseline prompts (REASONING_PROMPT_V1)
- Document prompt optimization as incomplete, defer to Task 008
- Proceed with other phases (instrumentation, model selection, orchestrator)

**If RISK-007-005 occurs (time overrun)**:
- Complete Phases 1-4 (HIGH priority)
- Defer Phases 5-6 (MEDIUM priority) to Task 008
- Mark Task 007 as "Partial Success" (4/5 metrics achieved)

---

**Last Updated**: 2025-10-14
**Next File**: assumptions.md
