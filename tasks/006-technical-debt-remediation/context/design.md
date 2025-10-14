# Design - Task 006: Technical Debt Remediation

## Overview

This task remediates technical debt identified in Tasks 001-005, focusing on:
1. **Code complexity reduction** (4 functions: CCN 42/25/15/12 → ≤10)
2. **Type safety hardening** (mypy --strict compliance on CP files)
3. **Production resilience** (rate limiting, retry logic, connection pooling)
4. **Data integrity** (SHA256 hashes, reproducibility documentation)

**Design Principle**: Surgical refactoring with zero functional regressions

---

## Architecture

### 1. Complexity Reduction Strategy

#### Pattern: Extract Method Refactoring
**Technique**: Decompose high-CCN functions into smaller, single-responsibility functions

**Target Functions**:
```
services/langgraph/workflow.py:
  - reasoning_step (CCN=42) → Extract:
    - _try_orchestrator_glossary()
    - _check_scope_and_defuse()
    - _build_reasoning_prompt()
    - _invoke_llm_reasoning()
    - _update_metadata()

  - retrieval_step (CCN=25) → Extract:
    - _extract_filters()
    - _perform_graph_traversal()
    - _rerank_results()
    - _format_retrieval_output()

services/graph_index/graph_traverser.py:
  - _build_edge_index (CCN=15) → Extract:
    - _index_well_edges()
    - _index_curve_edges()
    - _index_site_edges()

  - expand_search_results (CCN=12) → Extract:
    - _expand_well_nodes()
    - _expand_curve_nodes()
    - _expand_site_nodes()
```

**Refactoring Constraints**:
- No changes to public APIs (function signatures preserved)
- No changes to function behavior (output identical for same input)
- All extracted functions are private (prefix with `_`)
- Maintain existing error handling

---

### 2. Type Safety Architecture

#### Pattern: Gradual Typing with Protocol Types

**Strategy**:
```python
from typing import Protocol, Union, Optional, Dict, List, Any

# Before (implicit Any)
def reasoning_step(state):
    result = orchestrator.invoke(state.query)
    return result

# After (explicit types)
def reasoning_step(state: WorkflowState) -> WorkflowState:
    result: Dict[str, Any] = orchestrator.invoke(state.query)
    return state
```

**Type Fixes Required**:

**workflow.py**:
- Add `WorkflowState` type hints to all step functions
- Replace `dict` → `Dict[str, Any]` for metadata
- Annotate `Optional[str]` for nullable fields
- Use `Union[X, Y]` for multi-type returns

**graph_traverser.py**:
- Type NetworkX graph: `nx.DiGraph` → `nx.DiGraph[str]` (node IDs are strings)
- Annotate return types: `List[Tuple[str, Dict[str, Any]]]`
- Use `TypedDict` for node attribute dictionaries

**mypy.ini Configuration** (if needed):
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

---

### 3. Resilience Architecture

#### 3.1 Glossary Scraper Resilience

**Component**: `mcp_server.py` → `get_dynamic_definition()`

**Design**:
```
┌─────────────────────────────────────────────────────┐
│         get_dynamic_definition(term)                │
├─────────────────────────────────────────────────────┤
│  1. Check Redis cache (15min TTL)                   │
│  2. If miss:                                         │
│     a. Rate limiter (1 req/sec per domain)          │
│     b. Try scrape from SLB                          │
│        - Multiple CSS selectors:                    │
│          ['.definition', '[itemprop="description"]',│
│           'div.glossary-content']                   │
│        - Health check: len(text) >= 10              │
│        - Timeout: 5s (connect: 2s, read: 3s)        │
│     c. If fail (HTTP 429):                          │
│        - Exponential backoff: 1s, 2s, 4s           │
│        - Max retries: 3                             │
│     d. If still fail, try SPE                       │
│     e. If still fail, try AAPG                      │
│     f. If all fail, return static glossary          │
│  3. Cache result in Redis + in-memory               │
│  4. Return definition                                │
└─────────────────────────────────────────────────────┘
```

**Implementation**:
```python
import redis
from functools import wraps
import time

class RateLimiter:
    """Token bucket rate limiter (1 req/sec per domain)"""
    def __init__(self, rate=1.0):
        self.rate = rate
        self.allowance = 1.0
        self.last_check = time.time()

    def allow_request(self) -> bool:
        current = time.time()
        elapsed = current - self.last_check
        self.last_check = current
        self.allowance += elapsed * self.rate
        if self.allowance > 1.0:
            self.allowance = 1.0
        if self.allowance < 1.0:
            return False
        self.allowance -= 1.0
        return True

rate_limiters = {
    'slb': RateLimiter(rate=1.0),
    'spe': RateLimiter(rate=1.0),
    'aapg': RateLimiter(rate=1.0)
}

def scrape_with_fallback(term: str, sources: List[str]) -> Optional[Dict]:
    """Try multiple sources with CSS fallbacks"""
    for source in sources:
        # Rate limiting
        if not rate_limiters[source].allow_request():
            time.sleep(1.0)  # Wait for token

        # Try multiple CSS selectors
        for selector in CSS_SELECTORS[source]:
            try:
                response = requests.get(url, timeout=(2, 3))
                if response.status_code == 429:
                    # Exponential backoff
                    for delay in [1, 2, 4]:
                        time.sleep(delay)
                        response = requests.get(url, timeout=(2, 3))
                        if response.status_code == 200:
                            break

                text = parse_html(response.text, selector)
                if len(text) >= 10:  # Health check
                    return {'definition': text, 'source': source}
            except Exception as e:
                logger.warning(f"Scrape failed: {source}/{selector}: {e}")
                continue

    # Fallback to static glossary
    return STATIC_GLOSSARY.get(term)
```

---

#### 3.2 Redis Resilience

**Component**: `mcp_server.py` → Caching layer

**Design**:
```
┌───────────────────────────────────────────┐
│     RedisCache (Primary)                  │
│  - Connection pool (max 10, timeout 1s)   │
│  - Health check every 60s                 │
│  - Auto-reconnect on failure              │
└───────────────┬───────────────────────────┘
                │
                ▼ (fallback on failure)
┌───────────────────────────────────────────┐
│     InMemoryCache (Fallback)              │
│  - functools.lru_cache (max 1000 entries) │
│  - No TTL (lives until process restart)   │
└───────────────────────────────────────────┘
```

**Implementation**:
```python
import redis
from functools import lru_cache
from typing import Optional

class ResilientCache:
    def __init__(self):
        self.redis_client = None
        self.redis_available = False
        self.failure_count = 0
        self._init_redis()

    def _init_redis(self):
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                socket_connect_timeout=1,
                socket_timeout=1,
                connection_pool=redis.ConnectionPool(max_connections=10)
            )
            self.redis_client.ping()
            self.redis_available = True
            self.failure_count = 0
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self.redis_available = False

    def get(self, key: str) -> Optional[str]:
        # Try Redis first
        if self.redis_available:
            try:
                value = self.redis_client.get(key)
                if value:
                    return value.decode('utf-8')
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
                self.failure_count += 1
                if self.failure_count >= 3:
                    self.redis_available = False

        # Fallback to in-memory cache
        return self._in_memory_get(key)

    @lru_cache(maxsize=1000)
    def _in_memory_get(self, key: str) -> Optional[str]:
        # This is populated by set() calls
        return None

    def set(self, key: str, value: str, ttl: int = 900):
        # Try Redis
        if self.redis_available:
            try:
                self.redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
                self.failure_count += 1

        # Always set in-memory (fallback)
        # Note: lru_cache doesn't support set, so use a dict
        self.in_memory_store[key] = value
```

---

#### 3.3 External API Retry Logic

**Components**:
- **AstraDB**: Vector search in `services/langgraph/workflow.py:retrieval_step`
- **WatsonX AI**: LLM calls in `services/langgraph/workflow.py:reasoning_step`

**Design**:
```python
from functools import wraps
import time

def retry_with_backoff(max_retries=3, backoff_delays=[1, 2, 4]):
    """Decorator for exponential backoff retry"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    if attempt < max_retries - 1:
                        delay = backoff_delays[attempt]
                        logger.warning(f"Retry {attempt+1}/{max_retries} after {delay}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted for {func.__name__}")
                        raise
        return wrapper
    return decorator

# Usage in workflow.py
@retry_with_backoff(max_retries=3, backoff_delays=[1, 2, 4])
def _query_astradb_vector_search(query_embedding, top_k=10):
    """Query AstraDB with retry logic"""
    collection = get_astradb_collection()
    results = collection.vector_find(
        query_embedding,
        limit=top_k,
        include_similarity=True
    )
    return results

# Embedding caching
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str) -> List[float]:
    """Cache WatsonX embeddings to reduce API calls"""
    return watsonx_embed_client.embed(text)
```

---

## Data Strategy

### 1. Data Integrity: SHA256 Hashing

**Requirement**: Document SHA256 hashes for all test data (SCA §2.2, §2.9)

**Implementation**:
```bash
# Generate hashes
cd "C:\projects\Work Projects\astra-graphrag"
sha256sum tests/fixtures/e2e_qa_pairs.json > tasks/006-technical-debt-remediation/artifacts/sha256sums.txt
```

**Update data_sources.json**:
```json
{
  "inputs": [
    {
      "id": "e2e_qa_pairs",
      "file_path": "tests/fixtures/e2e_qa_pairs.json",
      "sha256": "abc123...",
      "rows": 55,
      "columns": 3,
      "licensing": "internal",
      "pii": false,
      "retention_days": null
    }
  ]
}
```

---

### 2. Reproducibility Documentation

**File**: `REPRODUCIBILITY.md` (root directory)

**Contents**:
```markdown
# Reproducibility Guide - astra-graphrag

## Environment Setup

**Python Version**: 3.11.9
**OS**: Windows 10 (64-bit)
**Virtual Environment**: venv

### Installation Steps
1. Clone repository: `git clone https://github.com/krump3t/astra-graphrag.git`
2. Create venv: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
4. Install dependencies: `pip install -r requirements.txt`

## Running Tests

### Critical Path E2E Tests
```bash
pytest tests/critical_path/test_cp_workflow_e2e.py -v
```

### Full Test Suite
```bash
pytest tests/ -v --cov=services --cov=mcp_server
```

## Environment Variables

Create `.env` file in `configs/env/` with:
```
ASTRA_DB_APPLICATION_TOKEN=<token>
ASTRA_DB_API_ENDPOINT=<endpoint>
OPENAI_API_KEY=<key>
WATSONX_API_KEY=<key>
WATSONX_PROJECT_ID=<id>
```

## Data Requirements

**FORCE 2020 Dataset**: 118 LAS files in `data/raw/force2020/las_files/`
**SHA256 Verification**: `sha256sum -c tasks/006-technical-debt-remediation/artifacts/sha256sums.txt`
```

---

## Verification Strategy

### 1. Complexity Verification

**Tool**: Lizard

**Command**:
```bash
lizard -C 10 services/langgraph/workflow.py services/graph_index/graph_traverser.py
```

**Expected Output**:
```
================================================
  NLOC    CCN   token  PARAM  length  location
------------------------------------------------
      20      5    117      2      34 reasoning_step (after refactor)
      25      8    200      1      40 retrieval_step (after refactor)
      10      4     80      1      15 _build_edge_index (after refactor)
       8      3     60      4      12 expand_search_results (after refactor)
```

**Validation**: All functions CCN≤10, no warnings

---

### 2. Type Safety Verification

**Tool**: mypy --strict

**Command**:
```bash
mypy --strict services/langgraph/workflow.py services/graph_index/graph_traverser.py
```

**Expected Output**:
```
Success: no issues found in 2 source files
```

**Validation**: 0 errors, 0 warnings

---

### 3. Regression Testing

**Tool**: pytest + coverage

**Command**:
```bash
pytest tests/critical_path/test_cp_workflow_e2e.py -v --cov=services.langgraph.workflow --cov=services.graph_index.graph_traverser --cov-report=term-missing
```

**Expected Output**:
```
==================== 19 passed in 51.23s ====================
Coverage: 100% (no regressions)
```

**Validation**: All 19 tests pass, coverage ≥95%

---

### 4. Resilience Testing

**Test Suite**: `tasks/006-technical-debt-remediation/artifacts/validation/test_resilience.py`

**Scenarios**:
1. **Rate Limiting**: Simulate 10 requests/sec → Expect rate limiter to enforce 1 req/sec
2. **Redis Failure**: Stop Redis → Expect fallback to in-memory cache
3. **AstraDB Timeout**: Mock timeout → Expect 3 retries with backoff
4. **HTTP 429**: Mock rate limit error → Expect exponential backoff
5. **Scraper Fallback**: Mock SLB failure → Expect SPE/AAPG/static fallback

**Command**:
```bash
pytest tasks/006-technical-debt-remediation/artifacts/validation/test_resilience.py -v
```

**Expected Output**:
```
==================== 5 passed in 10.45s ====================
```

---

## Phase Breakdown

### Phase 1: Context (30 min) ✅
- hypothesis.md, design.md, evidence.json, data_sources.json, adr.md, risks.md, assumptions.md, glossary.md

### Phase 2: Complexity Refactoring (3-4 hours)
1. Refactor `reasoning_step`: Extract 5 helper functions
2. Refactor `retrieval_step`: Extract 4 helper functions
3. Refactor `_build_edge_index`: Extract 3 helper functions
4. Refactor `expand_search_results`: Extract 3 helper functions
5. Run lizard after each refactor (verify CCN≤10)
6. Run pytest after each refactor (verify 0 regressions)

### Phase 3: Type Safety (1-2 hours)
1. Add type hints to `reasoning_step`, `retrieval_step` (workflow.py)
2. Add type hints to `_build_edge_index`, `expand_search_results` (graph_traverser.py)
3. Fix mypy --strict errors iteratively
4. Run pytest (verify 0 regressions)

### Phase 4: Resilience (2-3 hours)
1. Implement `RateLimiter` class
2. Add multi-selector scraping with health checks
3. Implement `ResilientCache` (Redis + in-memory fallback)
4. Add `@retry_with_backoff` decorator
5. Apply to AstraDB and WatsonX calls
6. Write resilience test suite
7. Run tests (verify 99%+ success rate)

### Phase 5: Data Integrity (1 hour)
1. Generate SHA256 hashes
2. Update data_sources.json
3. Create REPRODUCIBILITY.md
4. Upgrade pip to 25.3
5. Run pip-audit (verify 0 high/critical)

### Phase 6: QA & Validation (1 hour)
1. Run full test suite (19 E2E + resilience tests)
2. Run QA gates: ruff, mypy --strict, lizard, pip-audit
3. Generate validation report
4. Git commit and push

---

## Success Metrics

| Metric | Baseline | Target | Achieved |
|--------|----------|--------|----------|
| Max CCN | 42 | ≤10 | TBD |
| mypy errors | >35 | 0 | TBD |
| Vulnerabilities | 0 | 0 | TBD |
| Scraper success | Unknown | ≥99% | TBD |
| Redis availability | Unknown | ≥99.9% | TBD |
| Test pass rate | 19/19 | 19/19 | TBD |

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Status**: Context phase (Phase 1)
**Next**: evidence.json (P1 sources for refactoring best practices)
