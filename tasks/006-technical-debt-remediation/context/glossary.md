# Glossary - Task 006

## Refactoring Terms

### Cyclomatic Complexity (CCN)
**Definition**: Software metric measuring the number of linearly independent paths through a program's source code. Calculated by counting decision points (if, while, for, case) + 1.

**Formula**: CCN = E - N + 2P (where E=edges, N=nodes, P=connected components in control flow graph)

**Thresholds**:
- CCN ≤10: Low complexity (easy to maintain)
- 11-20: Moderate complexity (needs refactoring)
- 21-50: High complexity (difficult to test, high defect risk)
- >50: Very high complexity (unmaintainable)

**Source**: McCabe (1976)

---

### Extract Method
**Definition**: Refactoring pattern where a code fragment is moved into a new method, replacing the fragment with a call to the new method.

**Purpose**: Reduce function complexity, improve readability, enable reuse

**Example**:
```python
# Before
def foo():
    # 50 lines of code
    x = complex_calculation()
    y = x * 2
    return y

# After (Extract Method)
def foo():
    # 45 lines of code
    return _apply_transform(complex_calculation())

def _apply_transform(x):
    return x * 2
```

**Source**: Fowler (2018), Refactoring: Improving the Design of Existing Code

---

### Gradual Typing
**Definition**: Type system where types can be added incrementally to dynamically typed code (Python), allowing mix of typed and untyped code in same codebase.

**Tools**: mypy, Pyright, Pyre

**Example**:
```python
# Untyped
def add(a, b):
    return a + b

# Gradually typed
def add(a: int, b: int) -> int:
    return a + b
```

---

### Critical Path (CP)
**Definition**: Set of modules/functions that must work correctly for core system functionality. In this task: workflow.py, graph_traverser.py, mcp_server.py.

**Importance**: CP components receive highest priority for testing, refactoring, and QA gates.

---

## Resilience Terms

### Exponential Backoff
**Definition**: Retry strategy where wait time increases exponentially between attempts (e.g., 1s, 2s, 4s, 8s).

**Purpose**: Reduce load on failing systems, give transient failures time to recover

**Jitter**: Random variation added to backoff delays to prevent synchronized retries (not used in Task 006)

**Example**:
```python
for attempt in range(3):
    try:
        result = api_call()
        break
    except TimeoutError:
        delay = 2 ** attempt  # 1s, 2s, 4s
        time.sleep(delay)
```

**Source**: Google Cloud Architecture Best Practices

---

### Rate Limiting
**Definition**: Technique to control the rate of requests to a system, preventing abuse or overload.

**Common Algorithms**:
- **Token Bucket**: Allows bursts, refills tokens at fixed rate (used in Task 006)
- **Leaky Bucket**: Smooths bursts, processes requests at fixed rate
- **Fixed Window**: Simple counter per time window (can allow bursts at boundaries)
- **Sliding Window**: Rolling time window (more complex, better burst control)

**Implementation** (Token Bucket):
```python
class RateLimiter:
    def __init__(self, rate=1.0):  # 1 request per second
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
```

---

### Connection Pooling
**Definition**: Technique where database/service connections are reused instead of creating new connections for each request.

**Benefits**:
- Reduces connection overhead (3-5x throughput increase for Redis)
- Lowers latency (60% reduction)
- Limits max connections (prevents resource exhaustion)

**Configuration**:
```python
redis.ConnectionPool(
    max_connections=10,  # Limit concurrent connections
    timeout=1.0          # Fail fast if pool exhausted
)
```

---

### Graceful Degradation
**Definition**: Design principle where system continues operating at reduced capacity when components fail, rather than failing completely.

**Example**: Redis cache fails → fallback to in-memory cache (slower, but functional)

**Contrast**: Fail-fast (immediately error on failure, no degradation)

---

### Circuit Breaker
**Definition**: Design pattern that detects failures and prevents repeated failing calls (not implemented in Task 006, deferred to future work).

**States**:
- **Closed**: Normal operation (requests pass through)
- **Open**: Failure threshold reached (requests fail immediately)
- **Half-Open**: Test recovery (allow 1 request to check if service recovered)

---

## Type Safety Terms

### mypy --strict
**Definition**: Strictest mode of mypy type checker, requiring:
- All functions have type annotations
- No `Any` types (explicit only)
- No implicit `Optional` (must use `Optional[T]`)
- No untyped calls

**Benefits**: Catches 15% of bugs (Gao et al. 2017)

**Example Errors**:
```python
# Error: Function missing return type annotation
def foo(x):  # mypy: error
    return x * 2

# Fixed
def foo(x: int) -> int:
    return x * 2
```

---

### Protocol Type
**Definition**: Structural subtyping in Python (PEP 544), allowing duck typing with type safety.

**Use Case**: When object behavior matters more than inheritance

**Example**:
```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()  # mypy OK if obj has draw() method
```

---

### Union Type
**Definition**: Type that can be one of several types (`Union[int, str]` or `int | str` in Python 3.10+)

**Example**:
```python
def foo(x: Union[int, str]) -> str:
    return str(x)
```

---

### Optional Type
**Definition**: Shorthand for `Union[T, None]`, indicating a value may be None

**Example**:
```python
def foo(x: Optional[int] = None) -> int:
    return x or 0
```

---

## Data Integrity Terms

### SHA-256
**Definition**: Cryptographic hash function producing 256-bit (64 hex char) digest, used for data integrity verification.

**Properties**:
- Deterministic (same input → same hash)
- Collision-resistant (computationally infeasible to find two inputs with same hash)
- One-way (cannot reverse hash to get input)

**Usage**:
```bash
sha256sum file.json  # Output: abc123...def456 file.json
```

**Standard**: NIST FIPS 180-4

---

### Reproducibility
**Definition**: Ability to regenerate exact results from a scientific study or software test, given the same data and environment.

**Requirements**:
- Pinned dependency versions (requirements.txt)
- Documented environment (Python version, OS)
- Deterministic algorithms (fixed seeds, no randomness)
- Data integrity verification (SHA-256 hashes)

---

## Testing Terms

### Regression Testing
**Definition**: Re-running existing test suite after code changes to ensure no existing functionality broke.

**Purpose**: Detect unintended side effects of refactoring

**Task 006 Usage**: Run 19 E2E tests after each function refactor (expect 19/19 pass)

---

### Smoke Test
**Definition**: Preliminary test to verify basic functionality before running full test suite.

**Purpose**: Fail fast if environment broken (e.g., API unavailable)

**Task 006 Usage**: 1-2 test queries to AstraDB/WatsonX before running full suite

---

### Integration Test
**Definition**: Test that verifies multiple components work together correctly (contrast: unit test tests single component in isolation).

**Task 006 Usage**: Resilience tests (Redis + scraper + rate limiter working together)

---

## Metrics Terms

### NLOC (Non-Comment Lines of Code)
**Definition**: Lines of code excluding comments and blank lines, used to measure code size.

**Task 006 Baseline**:
- reasoning_step: 130 NLOC
- retrieval_step: 133 NLOC

**Target**: ±10% change after refactoring (allow small increase for clarity)

---

### P95 Latency
**Definition**: 95th percentile of response times (5% of requests slower than this value).

**Usage**: Better metric than average (P50) for user experience, ignores outliers (unlike P99)

**Task 006 Target**: ≤5s for full workflow (verified in Task 004)

---

### Code Coverage
**Definition**: Percentage of code lines/branches executed during testing.

**Types**:
- **Line Coverage**: % of lines executed
- **Branch Coverage**: % of if/else branches taken (stricter metric)

**Task 006 Target**: ≥95% branch coverage on CP files

---

## SCA Protocol Terms

### Context Gate
**Definition**: SCA protocol requirement that context files (hypothesis.md, design.md, evidence.json, etc.) must be complete before coding begins.

**Purpose**: Ensure task is well-defined, evidence-based, and measurable

---

### P1/P2 Evidence
**Definition**: Priority classification for evidence sources
- **P1**: Primary sources (peer-reviewed papers, technical standards, official docs)
- **P2**: Secondary sources (blog posts, tutorials, Stack Overflow)

**SCA Requirement**: ≥3 P1 sources per task

---

### Authenticity Invariant
**Definition**: SCA principle requiring genuine computation (no placeholders, no fabricated results, no mocked data in production).

**Task 006 Application**: Run real lizard/mypy/pytest, not simulated outputs

---

## Document Metadata

**Created**: 2025-10-14
**Task ID**: 006
**Protocol**: SCA v9-Compact
**Total Terms**: 27
**Categories**: Refactoring (4), Resilience (5), Type Safety (4), Data Integrity (2), Testing (3), Metrics (3), SCA (3), Miscellaneous (3)
