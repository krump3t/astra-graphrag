# Design: E2E Progressive Complexity Validation Framework [DES]

**Task ID**: 021-e2e-progressive-validation
**Date**: 2025-10-16
**Protocol**: SCA Full Protocol v12.2

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     Astra GraphRAG System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  External        Public API         Internal Pipeline           │
│  ┌─────────┐    ┌───────────┐      ┌──────────────────┐       │
│  │ HTTP    │───>│ FastAPI   │─────>│ MCP Server       │       │
│  │ Client  │    │ Endpoint  │      │ (Tool Router)    │       │
│  └─────────┘    └───────────┘      └──────────────────┘       │
│                                              │                   │
│                                              ▼                   │
│                                     ┌──────────────────┐        │
│                                     │ Multi-Tool       │        │
│                                     │ Orchestrator     │        │
│                                     └──────────────────┘        │
│                                              │                   │
│                                              ▼                   │
│                                     ┌──────────────────┐        │
│                                     │ LangGraph        │        │
│                                     │ Workflow         │        │
│                                     └──────────────────┘        │
│                                              │                   │
│                  ┌───────────────────────────┴──────────┐       │
│                  ▼                                      ▼        │
│         ┌──────────────┐                     ┌──────────────┐   │
│         │ Astra DB     │                     │ IBM Watsonx  │   │
│         │ Graph Query  │                     │ LLM API      │   │
│         └──────────────┘                     └──────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │   Task 021 Validation Framework        │
         │  ┌──────────────────────────────┐      │
         │  │ Progressive Complexity Test  │      │
         │  │ - 50+ queries (5 tiers)      │      │
         │  │ - Ground truth validation    │      │
         │  │ - Authenticity inspection    │      │
         │  │ - Failure mode detection     │      │
         │  └──────────────────────────────┘      │
         └────────────────────────────────────────┘
```

---

## Component Design

### 1. Progressive Complexity Test Framework

**File**: `scripts/validation/progressive_complexity_test.py`
**LOC**: ~400
**Purpose**: Orchestrate E2E test execution across all 5 tiers

**Key Classes**:

```python
class ProgressiveComplexityTest:
    """Main test orchestrator"""

    def __init__(self, config: TestConfig):
        self.queries = self._load_queries()
        self.ground_truth = self._load_ground_truth()
        self.http_client = self._setup_http_client()
        self.validators = {
            'ground_truth': GroundTruthValidator(),
            'authenticity': AuthenticityInspector(),
            'complexity': ComplexityScorer()
        }

    def run_tier(self, tier: int) -> TierResults:
        """Execute all queries for a specific tier"""
        queries = self._filter_by_tier(tier)
        results = []

        for query in queries:
            # Execute query via HTTP
            response = self._execute_query(query)

            # Validate response
            truth_match = self.validators['ground_truth'].validate(
                query, response
            )

            # Measure complexity
            complexity_score = self.validators['complexity'].score(query)

            results.append(QueryResult(
                query=query,
                response=response,
                correct=truth_match,
                complexity=complexity_score,
                latency_ms=response.elapsed_ms
            ))

        return TierResults(tier, results)

    def run_all_tiers(self) -> ValidationReport:
        """Execute complete validation suite"""
        tier_results = [self.run_tier(i) for i in range(1, 6)]

        # Aggregate metrics
        overall_accuracy = self._calculate_accuracy(tier_results)
        complexity_correlation = self._analyze_correlation(tier_results)

        # Authenticity check
        auth_results = self.validators['authenticity'].scan_pipeline()

        # Failure mode detection
        failure_modes = self._detect_failures(tier_results)

        return ValidationReport(
            tier_results=tier_results,
            overall_accuracy=overall_accuracy,
            complexity_correlation=complexity_correlation,
            authenticity=auth_results,
            failure_modes=failure_modes
        )
```

**Data Structures**:

```python
@dataclass
class QueryMetadata:
    id: str
    tier: int
    complexity_score: float
    text: str
    expected_answer: str
    ground_truth_source: str  # "db_query", "aggregation", "expert"
    tools_required: List[str]

@dataclass
class QueryResult:
    query: QueryMetadata
    response: str
    correct: bool
    complexity: float
    latency_ms: int
    tools_invoked: List[str]
    errors: List[str]

@dataclass
class TierResults:
    tier: int
    queries: List[QueryResult]
    accuracy: float
    avg_latency: float
    avg_complexity: float
```

**Execution Flow**:

```
1. Load test queries (test_queries.json)
2. Load ground truth data (ground_truth.json)
3. For each tier (1-5):
   a. Filter queries by tier
   b. For each query:
      - Send HTTP POST to /query endpoint
      - Measure latency
      - Validate response against ground truth
      - Score complexity
      - Log tool invocations
   c. Calculate tier metrics
4. Aggregate all-tier statistics
5. Run authenticity scan
6. Detect failure modes
7. Generate validation report
```

---

### 2. Ground Truth Validator

**File**: `scripts/validation/ground_truth_validator.py`
**LOC**: ~250
**Purpose**: Verify system responses against known correct answers

**Key Classes**:

```python
class GroundTruthValidator:
    """Validate responses against ground truth"""

    def __init__(self, db_connection=None):
        self.db = db_connection or self._setup_db()
        self.matchers = {
            'exact': self._exact_match,
            'numeric': self._numeric_match,
            'semantic': self._semantic_match,
            'contains': self._contains_match
        }

    def validate(self, query: QueryMetadata, response: str) -> ValidationResult:
        """Validate response against ground truth"""

        # Get ground truth
        truth = self._get_ground_truth(query)

        # Select appropriate matcher
        matcher = self.matchers[query.match_type]

        # Perform validation
        is_correct = matcher(response, truth)
        confidence = self._calculate_confidence(response, truth)

        return ValidationResult(
            correct=is_correct,
            confidence=confidence,
            expected=truth,
            actual=response,
            match_type=query.match_type
        )

    def _get_ground_truth(self, query: QueryMetadata) -> str:
        """Retrieve ground truth from appropriate source"""
        if query.ground_truth_source == "db_query":
            return self._query_database(query.truth_query)
        elif query.ground_truth_source == "aggregation":
            return self._load_precomputed(query.id)
        elif query.ground_truth_source == "expert":
            return self._load_expert_answer(query.id)
        else:
            raise ValueError(f"Unknown source: {query.ground_truth_source}")

    def _numeric_match(self, response: str, truth: str, tolerance: float = 0.05) -> bool:
        """Match numeric values with tolerance"""
        resp_val = self._extract_number(response)
        truth_val = float(truth)

        if resp_val is None:
            return False

        return abs(resp_val - truth_val) / truth_val <= tolerance

    def _semantic_match(self, response: str, truth: str) -> bool:
        """Semantic similarity for complex answers"""
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer('all-MiniLM-L6-v2')

        emb_resp = model.encode(response)
        emb_truth = model.encode(truth)

        similarity = cosine_similarity([emb_resp], [emb_truth])[0][0]

        return similarity >= 0.80  # 80% semantic match threshold
```

**Validation Strategies**:

| Tier | Match Type | Strategy | Example |
|------|-----------|----------|---------|
| 1 | Exact | String equality | "42 wells" == "42 wells" |
| 1-2 | Numeric | ±5% tolerance | 2850.5 ≈ 2900.0 |
| 2-3 | Contains | Substring match | "high porosity" in response |
| 3-4 | Semantic | Embedding similarity ≥0.80 | Paraphrased answers |
| 5 | Expert | Manual review | Novel inference validation |

---

### 3. Authenticity Inspector

**File**: `scripts/validation/authenticity_inspector.py`
**LOC**: ~200
**Purpose**: Verify no mocks/stubs in execution path

**Key Classes**:

```python
class AuthenticityInspector:
    """Scan for mocks and verify genuine computation"""

    PROHIBITED_PATTERNS = [
        r'from\s+unittest\.mock\s+import',
        r'import\s+mock',
        r'@patch\(',
        r'MagicMock\(',
        r'Mock\(',
    ]

    def scan_pipeline(self) -> AuthenticityReport:
        """Scan entire pipeline for authenticity violations"""

        violations = []

        # 1. Scan for mock imports
        mock_violations = self._scan_for_mocks()
        violations.extend(mock_violations)

        # 2. Verify real I/O latency
        io_violations = self._verify_io_latency()
        violations.extend(io_violations)

        # 3. Check variable outputs
        output_violations = self._check_variable_outputs()
        violations.extend(output_violations)

        # 4. Verify performance scaling
        scaling_violations = self._verify_scaling()
        violations.extend(scaling_violations)

        authenticity_rate = 1.0 - (len(violations) / self._total_checks())

        return AuthenticityReport(
            authenticity_rate=authenticity_rate,
            violations=violations,
            passed=authenticity_rate >= 0.95
        )

    def _scan_for_mocks(self) -> List[Violation]:
        """Scan Python files for mock usage"""
        violations = []

        for py_file in self._get_pipeline_files():
            content = py_file.read_text()

            for pattern in self.PROHIBITED_PATTERNS:
                if re.search(pattern, content):
                    violations.append(Violation(
                        type="mock_import",
                        file=str(py_file),
                        pattern=pattern,
                        severity="critical"
                    ))

        return violations

    def _verify_io_latency(self) -> List[Violation]:
        """Verify real network I/O (≥10ms)"""
        violations = []

        # Test HTTP endpoint
        start = time.perf_counter()
        requests.post("http://localhost:8000/query", json={"text": "test"})
        latency_ms = (time.perf_counter() - start) * 1000

        if latency_ms < 10:
            violations.append(Violation(
                type="fake_io",
                component="http_endpoint",
                measured_latency=latency_ms,
                severity="critical"
            ))

        # Test Astra DB
        start = time.perf_counter()
        db_client.count_documents("wells")
        db_latency = (time.perf_counter() - start) * 1000

        if db_latency < 5:
            violations.append(Violation(
                type="fake_io",
                component="astra_db",
                measured_latency=db_latency,
                severity="critical"
            ))

        return violations

    def _check_variable_outputs(self) -> List[Violation]:
        """Verify different inputs produce different outputs"""
        violations = []

        queries = [
            "How many wells?",
            "What is average porosity?",
            "Compare wells 15/9-13 and 16/1-2"
        ]

        responses = [self._execute_query(q) for q in queries]

        unique_responses = len(set(responses))

        if unique_responses < len(queries):
            violations.append(Violation(
                type="constant_output",
                component="pipeline",
                severity="critical"
            ))

        return violations
```

**Authenticity Checks**:

1. **Mock Detection**: Scan all pipeline files for unittest.mock imports
2. **I/O Latency**: Measure HTTP (≥10ms), DB (≥5ms), LLM (≥50ms)
3. **Variable Outputs**: 3 different queries must produce 3 different responses
4. **Performance Scaling**: Simple query < Complex query latency

---

### 4. Complexity Scorer

**File**: `scripts/validation/complexity_scorer.py`
**LOC**: ~150
**Purpose**: Calculate query complexity score (0-100)

**Complexity Factors**:

| Factor | Weight | Calculation |
|--------|--------|-------------|
| **Reasoning Steps** | 30% | Count of logical operations required |
| **Tool Invocations** | 25% | Number of MCP tools needed |
| **Data Scope** | 20% | Single well vs multi-well vs all wells |
| **Aggregations** | 15% | Count of statistical operations |
| **Novel Inference** | 10% | Requires domain expertise? |

**Implementation**:

```python
class ComplexityScorer:
    """Calculate query complexity (0-100 scale)"""

    def score(self, query: str) -> float:
        """Calculate overall complexity score"""

        factors = {
            'reasoning_steps': self._count_reasoning_steps(query),
            'tool_invocations': self._count_tools(query),
            'data_scope': self._score_data_scope(query),
            'aggregations': self._count_aggregations(query),
            'novel_inference': self._detect_novel_inference(query)
        }

        weights = {
            'reasoning_steps': 0.30,
            'tool_invocations': 0.25,
            'data_scope': 0.20,
            'aggregations': 0.15,
            'novel_inference': 0.10
        }

        score = sum(factors[k] * weights[k] * 100 for k in factors)

        return min(100.0, max(0.0, score))

    def _count_reasoning_steps(self, query: str) -> float:
        """Count logical operations (normalized 0-1)"""
        keywords = ['then', 'and then', 'after', 'compare', 'correlate']
        count = sum(1 for kw in keywords if kw in query.lower())
        return min(1.0, count / 3)  # 3+ steps = max score

    def _count_tools(self, query: str) -> float:
        """Estimate tool invocations needed"""
        tool_keywords = {
            'validate': 1,
            'compare': 1,
            'statistics': 1,
            'export': 1,
            'compute': 1
        }
        count = sum(tool_keywords.get(kw, 0) for kw in query.lower().split())
        return min(1.0, count / 4)  # 4+ tools = max score

    def _score_data_scope(self, query: str) -> float:
        """Score based on data breadth"""
        if 'all wells' in query.lower() or 'all blocks' in query.lower():
            return 1.0
        elif re.search(r'\d+/\d+-\d+.*and.*\d+/\d+-\d+', query):
            return 0.6  # Multiple specific wells
        elif re.search(r'\d+/\d+-\d+', query):
            return 0.2  # Single specific well
        else:
            return 0.4  # Unspecified scope
```

**Tier Mapping**:

```python
def assign_tier(complexity_score: float) -> int:
    """Map complexity score to tier"""
    if complexity_score < 20:
        return 1  # Simple
    elif complexity_score < 40:
        return 2  # Moderate
    elif complexity_score < 60:
        return 3  # Complex
    elif complexity_score < 80:
        return 4  # Advanced
    else:
        return 5  # Expert
```

---

## Data Structures

### Test Query Dataset

**File**: `data/test_queries.json`

```json
{
  "queries": [
    {
      "id": "tier1_001",
      "tier": 1,
      "complexity_score": 10.5,
      "text": "How many wells are in the database?",
      "expected_answer": "3",
      "match_type": "exact",
      "ground_truth_source": "db_query",
      "truth_query": "SELECT COUNT(*) FROM wells",
      "tools_required": ["query_knowledge_graph"],
      "expected_latency_ms": 200,
      "failure_modes": []
    },
    {
      "id": "tier2_001",
      "tier": 2,
      "complexity_score": 32.0,
      "text": "What is the average porosity for well 15/9-13?",
      "expected_answer": "0.22",
      "match_type": "numeric",
      "ground_truth_source": "aggregation",
      "precomputed_file": "ground_truth/tier2_001.json",
      "tools_required": ["query_knowledge_graph", "compute_curve_statistics"],
      "expected_latency_ms": 450,
      "failure_modes": ["missing_curve_data"]
    }
  ]
}
```

### Ground Truth Reference

**File**: `data/ground_truth.json`

```json
{
  "tier1_001": {
    "answer": "3",
    "source": "db_query",
    "query": "SELECT COUNT(*) FROM wells",
    "verified_date": "2025-10-16",
    "confidence": 1.0
  },
  "tier2_001": {
    "answer": "0.22",
    "source": "aggregation",
    "calculation": "AVG(porosity) WHERE well_id='15/9-13'",
    "verified_date": "2025-10-16",
    "confidence": 0.95,
    "tolerance": 0.05
  }
}
```

---

## Testing Strategy

### Differential Testing

Verify system produces different outputs for different inputs:

```python
def test_differential_outputs():
    """Verify outputs vary with inputs"""
    queries = [
        "How many wells?",
        "What is average porosity?",
        "Compare wells 15/9-13 and 16/1-2"
    ]

    responses = [execute_query(q) for q in queries]

    # All responses must be unique
    assert len(set(responses)) == len(responses), \
        "Different queries must produce different outputs"
```

### Sensitivity Testing

Verify small input changes produce measurable output changes:

```python
def test_sensitivity():
    """Verify sensitivity to input variations"""
    base_query = "What is porosity for well 15/9-13?"
    variant_query = "What is porosity for well 16/1-2?"

    response1 = execute_query(base_query)
    response2 = execute_query(variant_query)

    # Responses should differ (different wells)
    assert response1 != response2

    # But both should be valid numeric answers
    assert _extract_number(response1) is not None
    assert _extract_number(response2) is not None
```

### Performance Scaling

Verify latency scales with query complexity:

```python
def test_performance_scaling():
    """Verify complexity affects latency"""
    simple_query = "How many wells?"  # Tier 1
    complex_query = "Validate wells 15/9-13, 16/1-2, 25/10-10, compute statistics, export"  # Tier 4

    latency_simple = measure_latency(simple_query)
    latency_complex = measure_latency(complex_query)

    # Complex query should take longer
    assert latency_complex > latency_simple * 1.5
```

---

## Leakage Prevention

### Train/Test Separation

**None required** - This is validation only, no training involved

### Ground Truth Isolation

- Ground truth data stored separately from system knowledge graph
- Queries never include expected answers in text
- Validation logic independent of system implementation

### Temporal Consistency

- All test queries use data snapshot from specific date
- No dynamic queries that change with database updates
- Timestamps recorded for reproducibility

---

## Failure Mode Detection

### Category 1: Query Parsing Errors

**Detection**: Response contains "error" or "invalid"
**Example**: Malformed input triggers error message

### Category 2: Entity Extraction Failures

**Detection**: No well IDs extracted when expected
**Example**: "Well ABC" (invalid ID format) → extraction fails

### Category 3: Graph Traversal Dead-Ends

**Detection**: "No results found" when data exists
**Example**: Query for valid well returns empty

### Category 4: Aggregation Misclassification

**Detection**: Wrong aggregation type applied
**Example**: Asks for "average" but system returns "count"

### Category 5: LLM Hallucination

**Detection**: Response contains facts not in ground truth
**Example**: Invents well names or values

### Category 6: Timeout/Latency Violations

**Detection**: P95 latency > 5000ms
**Example**: Complex query takes 8 seconds

### Category 7: Incomplete/Partial Responses

**Detection**: Response missing expected components
**Example**: Compare query only shows one well

---

## Reporting

### Validation Report Structure

```markdown
# E2E Progressive Complexity Validation Report

## Executive Summary
- Overall Accuracy: 82% (target: ≥80%) ✅
- Tier 1-5 Accuracy: 96%, 87%, 78%, 68%, 54%
- Authenticity Rate: 97% (target: ≥95%) ✅
- Failure Detection: 92% (target: ≥90%) ✅

## Tier-by-Tier Analysis
### Tier 1: Simple Queries
- Accuracy: 96% (9/10 correct)
- Avg Latency: 185ms
- Failed Query: tier1_007 (missing data)

[... details for each tier ...]

## Correlation Analysis
- Complexity vs Accuracy: r = -0.94 (strong negative) ✅
- Linear regression: R² = 0.89
- Conclusion: Accuracy degrades predictably with complexity

## Authenticity Verification
- Mock imports detected: 0 ✅
- I/O latency measurements: All ≥10ms ✅
- Variable outputs: 100% verified ✅
- Performance scaling: Confirmed ✅

## Failure Mode Detection
- Category 1 (Parsing): 0 detected
- Category 2 (Extraction): 3 detected (30% of expected)
- Category 3 (Traversal): 1 detected (10% of expected)
[... etc ...]

## Recommendations
1. Improve entity extraction for ambiguous IDs
2. Add fallback for timeout scenarios
3. Expand ground truth coverage for Tier 5
```

---

## Dependencies

### Internal
- HTTP API endpoint (mcp_http_server.py)
- MCP tool implementations (validate, compare, statistics, export)
- LangGraph workflow (ReasoningOrchestrator)
- Astra DB connection
- IBM Watsonx API client

### External
- requests (HTTP client)
- pytest (test framework)
- pandas (data analysis)
- numpy (statistical calculations)
- scipy (correlation analysis)
- sentence-transformers (semantic matching, optional)

---

## Execution Plan

### Phase 1: Test Data Creation (Day 1)
1. Generate 50+ test queries
2. Compute ground truth via DB queries
3. Get domain expert validation for Tier 5

### Phase 2: Implementation (Days 2-3)
1. Implement ProgressiveComplexityTest
2. Implement GroundTruthValidator
3. Implement AuthenticityInspector
4. Implement ComplexityScorer
5. Create E2E test suite

### Phase 3: Validation (Day 4)
1. Execute all 50+ queries
2. Measure all metrics
3. Generate validation report

### Phase 4: Analysis (Day 5)
1. Tier-by-tier breakdown
2. Correlation analysis
3. Failure mode categorization
4. Recommendations

---

**Design Status**: Complete
**Protocol Compliance**: SCA Full Protocol v12.2
**Last Updated**: 2025-10-16
