# Testing & Optimization Guide

**Date**: 2025-10-09
**Purpose**: Complete guide to testing and optimizing the GraphRAG system

---

## Overview

This document provides comprehensive information about:
1. **LangGraph Workflow** - Model, prompts, and execution flow
2. **Test Suite** - 25 subsurface engineering questions with ground truth
3. **Logging & Traceability** - Complete workflow visibility for debugging
4. **Optimization Opportunities** - Data-driven improvement areas

---

## Part 1: LangGraph Workflow Analysis

### Model Configuration

| Component | Value |
|-----------|-------|
| **LLM Model** | `ibm/granite-13b-instruct-v2` |
| **Provider** | IBM Watsonx.ai |
| **Endpoint** | `https://us-south.ml.cloud.ibm.com` |
| **Embedding Model** | OpenAI `text-embedding-3-small` |
| **Vector Dimension** | 768 |
| **Database** | AstraDB (DataStax) |

### Workflow Stages

```
1. EMBEDDING STEP
   ├─ Query expansion (optional)
   ├─ Generate 768-dim embedding
   └─ Time: ~0.15s

2. RETRIEVAL STEP
   ├─ Vector search on AstraDB
   ├─ Hybrid reranking (70% vector, 30% keyword)
   ├─ Graph traversal (Phase 2 - if relationship query)
   └─ Time: ~0.8s

3. REASONING STEP
   ├─ Scope detection (out-of-scope filtering)
   ├─ Structured extraction (attribute queries)
   ├─ Aggregation handling (COUNT, LIST, etc.)
   ├─ LLM generation (Watsonx Granite 13B)
   └─ Time: ~0.5s

TOTAL: ~1.5s per query
```

### Prompt Template

**Location**: `configs/prompts/base_prompt.txt`

**Structure**:
```
You are a helpful assistant specializing in subsurface geological and hydrological data analysis.

Use ONLY the information provided in the Context below...

Context:
{{context}}

Question: {{question}}

[Few-shot examples for attribute extraction]

Answer: [Generated response]
```

**Key Features**:
- Domain-specific instructions (subsurface geology)
- Few-shot examples for attribute extraction
- Strict context-only instruction (no external knowledge)
- Fallback handling ("insufficient information")

### Complete Workflow Documentation

See **`docs/LANGGRAPH_WORKFLOW_ANALYSIS.md`** for:
- Detailed stage-by-stage breakdown
- All metadata fields explained
- Performance characteristics
- Optimization opportunities
- Code references

---

## Part 2: Subsurface Engineering Test Suite

### Test Configuration

**File**: `tests/evaluation/subsurface_engineering_test_suite.json`

**Total Questions**: 25
**Categories**: 6
- Petrophysical Interpretation (6 questions)
- Lithofacies Classification (4 questions)
- Reservoir Characterization (5 questions)
- Graph Relationship Queries (3 questions)
- Well Log Analysis (2 questions)
- Cross-Well Analysis (5 questions)

### Complexity Distribution

| Complexity | Count | Percentage |
|------------|-------|------------|
| Easy | 4 | 16% |
| Medium | 6 | 24% |
| High | 9 | 36% |
| Very High | 6 | 24% |

### Ground Truth Sources

1. **FORCE 2020 Dataset** (12 questions)
   - Direct from well/curve metadata
   - Verifiable from graph structure

2. **Graph Structure** (8 questions)
   - Edge traversal results
   - Node relationships

3. **Scientific Literature** (9 questions)
   - AAPG Wiki (petrophysics)
   - Kansas Geological Survey (well logs)
   - EPA (nuclear logging)
   - Zenodo (FORCE 2020 docs)

4. **Combined** (6 questions)
   - Graph query + domain knowledge

### Sample Questions

**Easy**: "What is the well name for well 15_9-13?"
- Expected: "Sleipner East Appr"
- Ground Truth: Direct attribute lookup
- Graph Traversal: Should activate

**Medium**: "What curves are available for well 15_9-13?"
- Expected: 21 curves
- Ground Truth: Edge count from graph
- Graph Traversal: Must activate

**High**: "For well 15_9-13, which curves would you use to calculate porosity?"
- Expected: NPHI, RHOB, DTC
- Ground Truth: Graph query + petrophysical knowledge
- Graph Traversal: Should activate

**Very High**: "If well 15_9-13 shows a 5-division neutron-density crossover in a sandstone interval, what does this likely indicate?"
- Expected: Gas-bearing zone
- Ground Truth: Verify curves exist + interpret
- Graph Traversal: Must activate
- Technical Knowledge: Required

---

## Part 3: Test Execution Script

### Script Features

**File**: `scripts/validation/subsurface_engineering_test.py`

**Capabilities**:
1. **Complete Workflow Logging**
   - Every stage logged separately
   - Full metadata dump for debugging
   - Performance timing per stage

2. **Ground Truth Validation**
   - 10+ validation types
   - Exact match, contains, numeric, etc.
   - Graph traversal verification

3. **Performance Metrics**
   - Latency breakdown by stage
   - Percentage contribution
   - Cumulative statistics

4. **Comprehensive Reports**
   - Detailed log file (all queries)
   - JSON summary with metrics
   - Pass/fail breakdown

### Usage

```bash
# Run complete test suite
python scripts/validation/subsurface_engineering_test.py

# Output files generated:
# - logs/subsurface_test_YYYYMMDD_HHMMSS.log  (detailed log)
# - logs/test_summary_YYYYMMDD_HHMMSS.json    (JSON summary)
```

### Log Structure

**Per Query**:
```
=========================================================================================
QUERY ID: petro_01
CATEGORY: petrophysical_interpretation
QUERY: What petrophysical curves are available for well 15_9-13?
=========================================================================================

--- EMBEDDING STEP ---
query_expanded: True
expanded_query: What well log curves petrophysical measurements...

--- RETRIEVAL STEP ---
initial_retrieval_count: 100
num_results: 10
reranked: True
filter_applied: None
auto_filter: {"domain": "subsurface"}

--- RELATIONSHIP DETECTION ---
is_relationship_query: True
relationship_type: well_to_curves
entities: {"well_id": "15_9-13"}
confidence: 0.95

--- GRAPH TRAVERSAL ---
targeted_well_search: True
num_results_after_traversal: 22
expansion_ratio: 22.0
retrieved_node_ids: ["force2020-well-15_9-13", "force2020-curve-0", ...]

--- REASONING STEP ---
scope_check: {"in_scope": true, "confidence": 0.95}
defusion_applied: False
structured_extraction: False

------------------------------------------------------------------------------------------
PERFORMANCE METRICS
------------------------------------------------------------------------------------------
embedding: 0.150s (10.0%)
retrieval: 0.750s (50.0%)
graph_traversal: 0.220s (14.7%)
reasoning: 0.525s (35.0%)
TOTAL: 1.500s
------------------------------------------------------------------------------------------

=========================================================================================
GENERATED ANSWER
=========================================================================================
21 curves found: DEPT (DEPTH), FORCE_2020_LITHOFACIES_CONFIDENCE, GR (Gamma Ray)...
=========================================================================================

=========================================================================================
VALIDATION RESULTS - petro_01
=========================================================================================
Ground Truth Met: True
Checks Passed: 8
Checks Failed: 0

PASSED CHECKS:
  [PASS] Contains required term: 'DEPT'
  [PASS] Contains required term: 'GR'
  [PASS] Contains required term: 'NPHI'
  [PASS] Contains required term: 'RHOB'
  [PASS] Count in range: 21 (expected 15-25)
  [PASS] Graph traversal applied as expected
  [PASS] Mentions: '15_9-13'
  [PASS] Factual accuracy maintained
=========================================================================================
```

### Validation Types

The script validates:

1. **Exact Match**: Answer contains exact expected string
2. **Must Include**: Required terms present (case-insensitive)
3. **Must Mention**: Important terms (for scoring)
4. **Should Mention**: Bonus terms (not required)
5. **Numeric Validation**: Exact counts, ranges
6. **Graph Traversal Check**: Was graph used as expected?
7. **Curve Retrieval**: Specific curves retrieved
8. **Factual Accuracy**: Overall correctness flag
9. **Behavior Validation**: Expected vs actual system behavior
10. **Technical Interpretation**: Domain knowledge applied correctly

---

## Part 4: Optimization Insights

### Where to Look for Optimization

#### 1. Latency Breakdown (from logs)

```
PERFORMANCE METRICS
embedding: 0.150s (10.0%)        ← Low priority (small %)
retrieval: 0.750s (50.0%)        ← HIGH PRIORITY (largest)
graph_traversal: 0.220s (14.7%)  ← Medium priority
reasoning: 0.525s (35.0%)        ← HIGH PRIORITY (second largest)
```

**Actionable**: Focus on retrieval (50%) and reasoning (35%)

#### 2. Graph Traversal Effectiveness

```
--- GRAPH TRAVERSAL ---
targeted_well_search: True       ← Good! Direct lookup worked
expansion_ratio: 22.0            ← Excellent! 1 well → 22 nodes
graph_traversal_applied: True    ← Confirmed activation
```

**Actionable**:
- If `targeted_well_search: False` → Improve entity extraction
- If `expansion_ratio < 10` → May need multi-hop
- If `graph_traversal_applied: False` on relationship query → Fix detection

#### 3. Query Expansion Analysis

```
--- EMBEDDING STEP ---
query_expanded: True
expanded_query: "What well log curves petrophysical..."
```

**Actionable**:
- Track when expansion helps vs hurts
- A/B test expansion on/off
- Refine synonym dictionary

#### 4. Retrieval Quality

```
--- RETRIEVAL STEP ---
initial_retrieval_count: 100
num_results: 10
retrieved_entity_types: ["las_curve", "las_curve", ...]  ← All curves (good!)
```

**Actionable**:
- If wrong entity types → Improve auto-filter
- If low num_results → Adjust reranking weights
- If high initial count but low final → Reranking too aggressive

#### 5. Answer Quality

```
VALIDATION RESULTS
Ground Truth Met: True
Checks Passed: 8
Checks Failed: 0
```

**Actionable**:
- Track pass rate per question category
- Identify patterns in failures
- Refine prompts for failing categories

### Optimization Priority Matrix

Based on workflow analysis:

| Optimization | Impact | Effort | Data Needed from Logs |
|--------------|--------|--------|-----------------------|
| **Retrieval Caching** | High | Low | Repeated queries in logs |
| **Prompt Engineering** | High | Medium | Answer quality per prompt version |
| **Model Selection** | High | High | Latency + quality tradeoff |
| **Reranking Weights** | Medium | Low | Retrieved vs final entity types |
| **Graph Index** | Medium | High | Expansion ratios, traversal times |
| **Query Expansion** | Medium | Medium | Expanded vs original query quality |

### How to Use Logs for Optimization

#### A. Identify Slow Queries
```python
# From test_summary.json
queries_by_latency = sorted(
    results["performance_metrics"],
    key=lambda x: x["total"],
    reverse=True
)

print("Slowest queries:")
for q in queries_by_latency[:5]:
    print(f"{q['query_id']}: {q['total']:.3f}s")
```

#### B. Find Graph Traversal Misses
```python
# Queries where graph should activate but didn't
for result in results:
    expected = result["expected_behavior"]
    actual = result["actual_behavior"]
    if expected and not actual:
        print(f"Graph traversal miss: {result['query_id']}")
        print(f"  Query: {result['query']}")
        print(f"  Detection confidence: {result['metadata']['relationship_detection']['confidence']}")
```

#### C. Analyze Failure Patterns
```python
# Group failures by category
failures_by_category = {}
for result in results:
    if not result["ground_truth_met"]:
        category = result["category"]
        failures_by_category.setdefault(category, []).append(result["query_id"])

print("Failures by category:")
for cat, queries in failures_by_category.items():
    print(f"{cat}: {len(queries)} failures")
    print(f"  {queries}")
```

---

## Part 5: Running Your First Test

### Step 1: Review Test Questions

The test suite is already created with 25 questions. Review them:

```bash
# View test questions
cat tests/evaluation/subsurface_engineering_test_suite.json | jq '.queries[] | {id, query, complexity}'
```

### Step 2: Run Test Suite

```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run tests
python scripts/validation/subsurface_engineering_test.py
```

### Step 3: Analyze Results

```bash
# View detailed log
tail -f logs/subsurface_test_*.log

# View summary
cat logs/test_summary_*.json | jq '.{total_queries, passed, failed, average_latency}'

# Find failures
cat logs/test_summary_*.json | jq '.results[] | select(.ground_truth_met == false) | {query_id, query}'
```

### Step 4: Iterate & Optimize

Based on results:

1. **Fix failing queries**: Check logs for why they failed
2. **Optimize slow queries**: Analyze performance metrics
3. **Refine prompts**: Update `configs/prompts/base_prompt.txt`
4. **Adjust parameters**: Modify retrieval limits, reranking weights
5. **Re-run tests**: Measure improvement

---

## Part 6: Key Files Reference

### Created Files

1. **`docs/LANGGRAPH_WORKFLOW_ANALYSIS.md`**
   - Complete workflow documentation
   - Model configuration
   - Prompt structure
   - Optimization opportunities

2. **`tests/evaluation/subsurface_engineering_test_suite.json`**
   - 25 test questions with ground truth
   - Validation criteria
   - Scientific references

3. **`scripts/validation/subsurface_engineering_test.py`**
   - Test execution script
   - Comprehensive logging
   - Performance metrics
   - Validation engine

4. **`docs/TESTING_AND_OPTIMIZATION_GUIDE.md`** (this file)
   - Complete testing guide
   - Optimization playbook
   - Usage instructions

### Existing Files Referenced

1. **`services/langgraph/workflow.py`**
   - Main workflow orchestration
   - 3-stage pipeline

2. **`services/graph_index/generation.py`**
   - Watsonx LLM client
   - Model: `ibm/granite-13b-instruct-v2`

3. **`configs/prompts/base_prompt.txt`**
   - LLM prompt template
   - Few-shot examples

4. **`services/config/settings.py`**
   - Configuration management
   - Model IDs, endpoints

---

## Part 7: Next Steps

### Immediate Actions

1. **Review test questions** - Ensure they cover your use cases
2. **Run baseline tests** - Establish current performance
3. **Analyze workflow logs** - Identify bottlenecks
4. **Prioritize optimizations** - Based on data

### Short-Term Optimizations (1-2 weeks)

1. **Prompt Engineering**
   - Add more few-shot examples
   - Refine instructions for common query types
   - A/B test prompt variations

2. **Retrieval Tuning**
   - Adjust reranking weights (70/30 baseline)
   - Optimize entity type detection
   - Fine-tune retrieval limits

3. **Caching Strategy**
   - Cache embeddings for common queries
   - Cache LLM responses for exact matches
   - Cache graph traversal results

### Long-Term Optimizations (1-3 months)

1. **Model Evaluation**
   - Benchmark Granite 13B vs 20B vs 34B
   - Compare with Llama 3, Mistral
   - Cost/quality tradeoff analysis

2. **Advanced Graph Features**
   - Multi-hop relationship queries
   - Cross-well analysis patterns
   - Temporal graph queries

3. **Production Deployment**
   - Implement caching layer (Redis)
   - Add monitoring/alerting
   - Optimize for scale

---

## Summary

You now have:

✅ **Complete workflow documentation** - Model, prompts, stages, metadata
✅ **25 test questions** - Real subsurface engineering queries with ground truth
✅ **Comprehensive test script** - Full logging, validation, performance metrics
✅ **Optimization playbook** - Data-driven improvement areas

**Next**: Run the test suite and analyze results!

```bash
python scripts/validation/subsurface_engineering_test.py
```

---

**Questions?** Check the detailed workflow analysis in `docs/LANGGRAPH_WORKFLOW_ANALYSIS.md`

**Ready to optimize?** Use logs to identify bottlenecks and iterate!
