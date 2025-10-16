# Hypothesis: E2E Progressive Complexity Validation Framework [HYP]

**Task ID**: 021-e2e-progressive-validation
**Date**: 2025-10-16
**Dependencies**: Tasks 001-020 (Complete system integration)
**Protocol**: SCA Full Protocol v12.2

---

## Authenticity Commitment

- No mock objects or stub functions in validation framework
- All test queries produce genuine system responses (real embeddings, graph queries, LLM reasoning)
- Performance measurements reflect actual system behavior
- Test assertions verify real computational outputs
- Ground truth comparisons use actual data from knowledge graph

---

## Primary Hypothesis (H1)

**Statement**: A progressive complexity E2E validation framework with 50+ test queries spanning 5 complexity tiers will demonstrate ≥80% accuracy across all tiers, ≥95% authentic computation (no mocks), and correctly identify ≥90% of failure modes in the complete Astra GraphRAG pipeline (HTTP endpoint → MCP orchestration → LangGraph workflow → Knowledge graph → LLM reasoning).

### Core Metrics & Thresholds (α = 0.05)

| Metric ID | Metric | Target | Threshold | Critical Path | Measurement Method |
|-----------|--------|--------|-----------|---------------|-------------------|
| M1 | Overall System Accuracy | ≥80% | ≥75% | ✓ | Correct answers / total queries |
| M2 | Tier 1 Accuracy (Simple) | ≥95% | ≥90% | ✓ | Direct lookup queries |
| M3 | Tier 2 Accuracy (Moderate) | ≥85% | ≥80% | ✓ | Single aggregation queries |
| M4 | Tier 3 Accuracy (Complex) | ≥75% | ≥70% | ✓ | Multi-step reasoning |
| M5 | Tier 4 Accuracy (Advanced) | ≥65% | ≥60% | ✓ | Multi-tool orchestration |
| M6 | Tier 5 Accuracy (Expert) | ≥50% | ≥45% | ✓ | Novel inference |
| M7 | Authenticity Verification | ≥95% | ≥90% | ✓ | No mocks, real I/O detected |
| M8 | Failure Mode Detection | ≥90% | ≥85% | ✓ | Known bugs identified |
| M9 | E2E Latency P95 | ≤3000ms | ≤5000ms | - | HTTP → response time |
| M10 | Ground Truth Coverage | ≥80% | ≥75% | ✓ | Verifiable facts used |

### Evidence Base

**Power Analysis**: Power = 0.80, α = 0.05, effect size d = 0.8 (large effect)
**Sample Size**: n ≥ 50 queries (10 per tier)
**Evidence Quality**: ≥5 P1 sources (existing tasks + domain datasets)

---

## Secondary Hypotheses

### H2: Progressive Complexity Scaling

**Statement**: System accuracy will decrease linearly with complexity tier, demonstrating ≥90% correlation between query complexity score and accuracy rate.

**Metrics**:
- Pearson correlation coefficient r ≥ 0.90 (complexity vs accuracy)
- Linear regression R² ≥ 0.80
- Slope significantly negative (p < 0.05)

**Complexity Scoring** (0-100):
- Tier 1 (Simple): 0-20 points - Direct fact retrieval
- Tier 2 (Moderate): 21-40 points - Single aggregation/comparison
- Tier 3 (Complex): 41-60 points - Multi-step reasoning
- Tier 4 (Advanced): 61-80 points - Multi-tool orchestration
- Tier 5 (Expert): 81-100 points - Novel inference/synthesis

### H3: Component Authenticity Validation

**Statement**: ≥95% of system components will demonstrate authentic computation (no hardcoded values, real I/O, variable outputs) across all 5 pipeline stages.

**Pipeline Stages**:
1. HTTP Endpoint (mcp_http_server.py)
2. MCP Orchestration (MultiToolOrchestratorStrategy)
3. LangGraph Workflow (ReasoningOrchestrator)
4. Knowledge Graph Query (Astra DB + graph traversal)
5. LLM Reasoning (IBM Watsonx / Claude)

**Authenticity Tests** (per stage):
- No mock objects detected in execution path
- Real network I/O latency measured (≥10ms)
- Variable outputs for different inputs
- Proper error handling for invalid inputs

### H4: Failure Mode Coverage

**Statement**: The validation framework will identify ≥90% of known failure modes across 7 categories with ≥95% precision (no false positives).

**Failure Categories**:
1. Query parsing errors (malformed input)
2. Entity extraction failures (missing well IDs)
3. Graph traversal dead-ends (no matching nodes)
4. Aggregation type misclassification
5. LLM hallucination detection
6. Timeout/latency violations (P95 > 5s)
7. Incomplete/partial responses

**Detection Method**:
- Known-bug test suite (queries that previously failed)
- Negative test cases (intentionally invalid)
- Boundary condition tests (edge cases)

### H5: Ground Truth Alignment

**Statement**: ≥80% of test queries will have verifiable ground truth answers from the knowledge graph, with ≥90% match rate between system output and ground truth.

**Ground Truth Sources**:
- Direct database queries (well count, depth ranges)
- Pre-computed aggregations (porosity statistics)
- Known relationships (well-operator mappings)
- Domain expert validation (subsurface engineering facts)

### H6: Multi-Tool Orchestration Validation

**Statement**: Queries requiring multi-tool orchestration (Tier 4+) will correctly invoke ≥2 tools in ≥85% of cases, with proper dependency resolution and parallel execution when possible.

**Orchestration Metrics**:
- Correct tool selection (compare, validate, statistics, export)
- Dependency order maintained (validate before compare)
- Parallelization opportunities exploited (≥30% savings when applicable)
- Zero circular dependency errors

---

## Critical Path

**Definition**: Components that must meet all Hard Gates (§6 of protocol).

**Critical Path Components**:
1. `scripts/validation/progressive_complexity_test.py` - Test execution framework
2. `scripts/validation/ground_truth_validator.py` - Truth verification
3. `scripts/validation/authenticity_inspector.py` - No-mock verification
4. `scripts/validation/complexity_scorer.py` - Query complexity analysis
5. `tests/e2e/test_progressive_queries.py` - 50+ test cases

**Non-Critical Path**:
- Test data fixtures (JSON files)
- Reporting scripts
- Visualization tools

---

## Exclusions & Scope Boundaries

**In Scope**:
- HTTP API endpoint testing (real requests)
- MCP server tool execution (validate, compare, statistics, export)
- LangGraph workflow orchestration
- Astra DB graph queries (real database)
- LLM reasoning (IBM Watsonx API calls)
- 50+ progressive complexity queries (5 tiers)
- Ground truth validation
- Authenticity verification (no mocks)
- Failure mode detection

**Out of Scope**:
- Load testing / stress testing (covered in Task 014)
- Security penetration testing
- UI/UX testing
- Multi-user concurrency testing
- Data ingestion validation (covered in Task 012)
- Model fine-tuning / hyperparameter optimization

---

## Baselines & Margins

### Baseline (Current State - Estimated)
- Overall accuracy: ~70% (based on Task 004 results: 42/50 = 84%)
- Simple query accuracy: ~90%
- Complex query accuracy: ~55%
- Authenticity: Unknown (no prior validation)
- Failure detection: ~60% (manual observation)

### Target Performance
- Overall accuracy: ≥80% (10-point improvement)
- Progressive tier accuracy: 95% → 85% → 75% → 65% → 50%
- Authenticity: ≥95% (first measurement)
- Failure detection: ≥90% (30-point improvement)

### Safety Margins
- Overall accuracy threshold: 75% (allows 5-point variance)
- Tier-specific thresholds: 5% below targets
- Authenticity threshold: 90% (allows 5% infrastructure noise)

---

## Power Analysis & Confidence Intervals

### Statistical Framework
- **α (Type I error)**: 0.05 (5% false positive rate)
- **Power (1 - β)**: 0.80 (80% chance to detect true effect)
- **Effect size**: d = 0.8 (large effect, Cohen's convention)
- **Sample size**: n = 50 queries (10 per tier)

### Confidence Intervals
- Overall accuracy: 80% ± 7% (95% CI)
- Tier 1 accuracy: 95% ± 4% (95% CI)
- Authenticity rate: 95% ± 3% (95% CI)
- Failure detection: 90% ± 5% (95% CI)

---

## Test Query Design (5 Tiers)

### Tier 1: Simple Direct Queries (Complexity: 0-20)
**Characteristics**: Single fact retrieval, no reasoning required

**Examples** (n=10):
1. "How many wells are in the database?"
2. "What is the depth of well 15/9-13?"
3. "List all operators in Block 15"
4. "What curves are available for well 16/1-2?"
5. "What is the maximum porosity value?"
6. "Show me the first 5 wells alphabetically"
7. "What is the date range of the dataset?"
8. "How many blocks are represented?"
9. "What is the total depth drilled across all wells?"
10. "List all unique curve names"

**Expected Accuracy**: ≥95%
**Ground Truth**: Direct database queries

### Tier 2: Moderate Aggregation Queries (Complexity: 21-40)
**Characteristics**: Single aggregation, simple comparison

**Examples** (n=10):
1. "What is the average porosity for well 15/9-13?"
2. "Compare the depth of wells 15/9-13 and 16/1-2"
3. "Which well has the highest gamma ray reading?"
4. "Count the number of wells with porosity data"
5. "What is the median depth across all wells?"
6. "Show wells with depth greater than 3000m"
7. "Calculate mean porosity for Block 15"
8. "Which operator has the most wells?"
9. "What percentage of wells have neutron porosity curves?"
10. "Find wells with similar porosity to 15/9-13"

**Expected Accuracy**: ≥85%
**Ground Truth**: Pre-computed aggregations

### Tier 3: Complex Multi-Step Reasoning (Complexity: 41-60)
**Characteristics**: 2-3 reasoning steps, relationship traversal

**Examples** (n=10):
1. "Validate wells 15/9-13 and 16/1-2, then compare their porosity"
2. "Find wells with high porosity (>0.25) and low gamma ray (<50 API)"
3. "Which blocks have average porosity above 0.20?"
4. "Identify wells with incomplete curve data and list missing curves"
5. "Compare porosity trends between Blocks 15 and 16"
6. "Find operator with highest average well depth"
7. "Detect wells with anomalous porosity values (>2 std dev)"
8. "Correlate gamma ray and porosity across all wells"
9. "Identify wells drilled in same year with similar depth"
10. "Find wells with both high porosity and high resistivity"

**Expected Accuracy**: ≥75%
**Ground Truth**: Domain expert validation

### Tier 4: Advanced Multi-Tool Orchestration (Complexity: 61-80)
**Characteristics**: 3+ tool invocations, parallel execution

**Examples** (n=10):
1. "Validate wells 15/9-13, 16/1-2, and 25/10-10, compute statistics for each, and export to Excel"
2. "Compare porosity across all wells in Block 15, validate data quality, and summarize"
3. "For each operator, calculate average porosity and gamma ray, then rank operators"
4. "Identify wells with missing curves, validate completeness, and generate remediation report"
5. "Compare depths across operators, validate data, export comparison matrix"
6. "Compute statistical summary for all curves in well 15/9-13, validate, export"
7. "Find top 5 wells by porosity, compare their depths, export ranked list"
8. "Validate all wells in Block 16, compute aggregations, export dashboard data"
9. "Compare gamma ray distributions between Blocks 15 and 25, export plots"
10. "Analyze porosity vs depth relationship, validate outliers, export regression data"

**Expected Accuracy**: ≥65%
**Ground Truth**: Partial (multi-step validation)

### Tier 5: Expert Novel Inference (Complexity: 81-100)
**Characteristics**: Novel synthesis, domain expertise required

**Examples** (n=10):
1. "Predict reservoir quality for well 15/9-13 based on porosity and gamma ray logs"
2. "Identify potential hydrocarbon zones across all wells using log signatures"
3. "Recommend drilling targets in Block 15 based on historical success"
4. "Assess data quality impact on reservoir modeling for Block 16"
5. "Synthesize exploration insights from multi-well correlation analysis"
6. "Evaluate completeness of dataset for machine learning applications"
7. "Suggest data acquisition priorities based on gaps in coverage"
8. "Generate hypothesis about facies distribution from curve patterns"
9. "Assess suitability of dataset for petrophysical property prediction"
10. "Recommend QC protocols based on observed data quality issues"

**Expected Accuracy**: ≥50%
**Ground Truth**: Domain expert review

---

## Calibration Plan

### Component: Query Complexity Scorer
- **Calibration Method**: Manual scoring of 20 queries by domain expert
- **Metrics**: Pearson correlation (expert vs automated score)
- **Recalibration Trigger**: r < 0.80
- **Fallback**: Manual complexity assignment

### Component: Ground Truth Validator
- **Calibration Method**: Cross-validation with database queries
- **Metrics**: Match rate (system output vs DB query)
- **Recalibration Trigger**: Match rate < 85%
- **Fallback**: Manual verification

### Component: Authenticity Inspector
- **Calibration Method**: Known-mock test (inject mock, verify detection)
- **Metrics**: Detection rate (100% expected)
- **Recalibration Trigger**: Detection < 100%
- **Fallback**: Manual code review

---

## Success Criteria

**Context Gate (Phase 0)**:
- ✓ hypothesis.md with 6 hypotheses
- ✓ design.md with architecture
- ✓ evidence.json with ≥5 P1 sources
- ✓ data_sources.json with test query dataset
- ✓ adr.md with decision rationale

**Hard Gates (Phase 4)**:
- All 50+ test queries execute successfully
- CP coverage ≥95% (validation scripts)
- mypy --strict = 0 on CP
- Lizard CCN ≤10, Cognitive ≤15
- No secrets, no high/critical vulnerabilities
- Overall accuracy ≥75% (threshold)
- Authenticity ≥90% (threshold)
- Failure detection ≥85% (threshold)

**Deliverables (Phase 5)**:
- 50+ progressive complexity test queries
- Ground truth validation framework
- Authenticity inspection system
- Failure mode detection reports
- POC report with tier-by-tier analysis
- Reproducible test suite

---

## References

**Internal Evidence** (P1):
- E-021-001: Task 004 E2E validation (42/50 = 84% baseline)
- E-021-002: Task 013 Multi-tool orchestration (32% parallelization)
- E-021-003: Task 014 HTTP API (P50=206ms, P95=1.2s)
- E-021-004: Task 015 Authenticity framework (100% validation)
- E-021-005: Data ingestion logs (well counts, curve statistics)

**External Evidence** (P2):
- To be added in evidence.json (evaluation methodologies, ground truth techniques)

---

## Critical Path Definition

[CP]
- scripts/validation/progressive_complexity_test.py
- scripts/validation/ground_truth_validator.py
- scripts/validation/authenticity_inspector.py
- scripts/validation/complexity_scorer.py
- tests/e2e/test_progressive_queries.py
[/CP]

---

**End of Hypothesis**
