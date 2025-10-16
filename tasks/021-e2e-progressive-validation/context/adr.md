# Architectural Decision Records [ADR]

**Task ID**: 021-e2e-progressive-validation
**Date**: 2025-10-16
**Protocol**: SCA Full Protocol v12.2

---

## ADR-021-001: 5-Tier Progressive Complexity Framework

### Status
**ACCEPTED** - 2025-10-16

### Context
Need to systematically evaluate system capability boundaries across query difficulty spectrum. Options include:
1. Binary (simple/complex) classification
2. 3-tier framework (easy/medium/hard)
3. 5-tier progressive framework (simple → expert)
4. Continuous complexity scoring without tiers

### Decision
Use **5-tier progressive complexity framework** with quantitative 0-100 scoring.

### Rationale
**Chosen: 5-Tier Framework**
- **Granularity**: Sufficient detail to identify capability boundaries without over-segmentation
- **Balance**: Each tier has ~10 queries, providing statistical validity per tier
- **Interpretability**: Clear progression (95% → 85% → 75% → 65% → 50% target accuracy)
- **Evidence**: Literature supports 5-level complexity (Chen et al. EMNLP 2022)

**Rejected: Binary Classification**
- Too coarse - cannot identify where system degrades
- No insight into performance scaling
- Insufficient for root cause analysis

**Rejected: Continuous Scoring Only**
- Harder to communicate to stakeholders
- Difficult to set clear success criteria
- Less actionable for targeted improvements

### Consequences
- ✅ Clear performance expectations per tier
- ✅ Actionable insights (e.g., "system struggles at Tier 4")
- ✅ Comparable to literature baselines
- ⚠️ Requires manual tier assignment validation
- ⚠️ Boundary queries (e.g., tier 2/3 edge) may be ambiguous

### Compliance
**Evidence**: E-021-006 (Chen et al. progressive complexity)
**Trade-offs**: Granularity vs simplicity - chose granularity

---

## ADR-021-002: Ground Truth Validation Strategy

### Status
**ACCEPTED** - 2025-10-16

### Context
Need verifiable correct answers for ≥80% of queries. Options:
1. Database queries only (100% objective, limited coverage)
2. Expert validation only (100% coverage, subjective)
3. Hybrid approach (DB + precomputed + expert)
4. Crowdsourced validation

### Decision
Use **hybrid 3-source approach**: Database queries (Tier 1-2), Pre-computed aggregations (Tier 2-3), Expert validation (Tier 4-5).

### Rationale
**Chosen: Hybrid Approach**
- **Coverage**: Achieves ≥80% target across all tiers
- **Objectivity**: 60% DB-derived (Tier 1-2) = 100% objective
- **Feasibility**: Expert validation for 20% (Tier 5) is manageable
- **Cost-effective**: Reuses existing DB and Task 012 data

**Rejected: DB Queries Only**
- Limited to Tier 1-2 (~40% coverage)
- Cannot validate complex reasoning or novel inference
- Insufficient for H5 validation

**Rejected: Expert Validation Only**
- Too time-intensive (50+ queries)
- Subjective for simple queries where DB is authoritative
- Higher cost, lower reliability

**Rejected: Crowdsourcing**
- Requires domain expertise (subsurface engineering)
- Quality control difficult
- Not feasible for proprietary data

### Consequences
- ✅ ≥80% ground truth coverage achieved
- ✅ Objective validation for majority (60%)
- ✅ Cost-effective use of domain expert time
- ⚠️ Tier 5 validation may have lower confidence (subjective)
- ⚠️ Pre-computed aggregations require one-time setup effort

### Compliance
**Evidence**: E-021-005 (DB statistics), E-021-007 (Wang et al. ground truth methods)
**Trade-offs**: Objectivity vs coverage - balanced with hybrid approach

---

## ADR-021-003: Authenticity Verification Method

### Status
**ACCEPTED** - 2025-10-16

### Context
Must prove ≥95% genuine computation across pipeline. Options:
1. Static code analysis only (scan for mocks)
2. Runtime behavior analysis only (I/O latency, outputs)
3. Comprehensive multi-method approach
4. Manual code review

### Decision
Use **comprehensive multi-method authenticity inspection**: Static analysis (mock detection) + Runtime analysis (I/O latency, output variance) + Differential testing.

### Rationale
**Chosen: Multi-Method Approach**
- **Completeness**: Covers all authenticity invariants (Protocol v12.2 §2)
- **Confidence**: Multiple independent checks reduce false negatives
- **Proven**: Task 015 achieved 100% verification with similar approach
- **Automated**: No manual review required

**Rejected: Static Analysis Only**
- Cannot detect hardcoded values or fake I/O
- Misses runtime behavior issues
- Incomplete coverage of invariants

**Rejected: Runtime Only**
- Cannot detect mocks in unexercised code paths
- Higher false negative risk
- Requires extensive test coverage

**Rejected: Manual Review**
- Not scalable
- Human error prone
- Not repeatable

### Consequences
- ✅ ≥95% authenticity verification achievable
- ✅ Comprehensive coverage of all invariants
- ✅ Automated and repeatable
- ⚠️ Requires implementation of authenticity_inspector.py (~200 LOC)
- ⚠️ Runtime checks add ~10-20ms per query (acceptable)

### Compliance
**Evidence**: E-021-004 (Task 015 100% authenticity verification)
**Trade-offs**: Implementation effort vs completeness - chose completeness

---

## ADR-021-004: Failure Mode Taxonomy

### Status
**ACCEPTED** - 2025-10-16

### Context
Need to categorize failures for root cause analysis. Options:
1. Binary (pass/fail) only
2. 3 categories (input/processing/output)
3. 7-category detailed taxonomy
4. Open-ended failure annotation

### Decision
Use **7-category failure taxonomy**: Query parsing, Entity extraction, Graph traversal, Aggregation misclassification, LLM hallucination, Timeout/latency, Incomplete responses.

### Rationale
**Chosen: 7-Category Taxonomy**
- **Actionable**: Each category maps to specific component
- **Comprehensive**: Covers observed failure modes from Task 004
- **Literature-supported**: Liu et al. ACL 2024 validates categorization
- **Balanced**: Granular enough for diagnosis, not too fine-grained

**Rejected: Binary Only**
- No diagnostic value
- Cannot guide improvements
- Insufficient for H4 validation

**Rejected: 3-Category Coarse**
- Too vague (e.g., "processing error" unhelpful)
- Cannot identify root causes
- Lower detection rate

**Rejected: Open-Ended**
- Inconsistent categorization
- Hard to aggregate statistics
- Not comparable across runs

### Consequences
- ✅ ≥90% failure detection rate achievable
- ✅ Root cause identification enables targeted fixes
- ✅ Comparable to academic baselines
- ⚠️ Requires manual category mapping for new failure types
- ⚠️ Some failures may fit multiple categories

### Compliance
**Evidence**: E-021-001 (Task 004 failures), E-021-008 (Liu et al. failure taxonomy)
**Trade-offs**: Granularity vs simplicity - chose granularity for actionability

---

## ADR-021-005: Semantic Similarity Threshold

### Status
**ACCEPTED** - 2025-10-16

### Context
Tier 3-4 queries need semantic matching (not exact). Options:
1. Exact string match only (strict, low recall)
2. High threshold 0.90+ (strict semantic)
3. Medium threshold 0.80 (balanced)
4. Low threshold 0.70 (permissive)

### Decision
Use **0.80 cosine similarity threshold** for semantic matching in Tier 3-4 queries.

### Rationale
**Chosen: 0.80 Threshold**
- **Literature-supported**: Wang et al. WWW 2023 recommends 0.75-0.85
- **Balanced**: Allows paraphrasing without accepting incorrect answers
- **Empirically validated**: Task 015 used similar thresholds successfully
- **Tier-appropriate**: Tier 3-4 complexity justifies semantic flexibility

**Rejected: Exact Match**
- Too strict for complex queries
- Penalizes correct but paraphrased answers
- Unrealistic for LLM-generated responses

**Rejected: 0.90+ High Threshold**
- Too strict - minor phrasing differences fail
- Lower effective coverage
- Not justified by use case

**Rejected: 0.70 Low Threshold**
- Too permissive - risks accepting incorrect answers
- Lower confidence in validation
- Not supported by literature

### Consequences
- ✅ Balanced precision/recall for Tier 3-4
- ✅ Accepts correct paraphrased answers
- ✅ Literature-validated threshold
- ⚠️ Requires sentence-transformers library (dependency)
- ⚠️ May need calibration if initial results show issues

### Compliance
**Evidence**: E-021-007 (Wang et al. semantic similarity thresholds)
**Trade-offs**: Strictness vs recall - chose balanced 0.80

---

## ADR-021-006: Test Query Count per Tier

### Status
**ACCEPTED** - 2025-10-16

### Context
Need sufficient statistical power while managing effort. Options:
1. 5 queries/tier (n=25 total, low power)
2. 10 queries/tier (n=50 total, medium power)
3. 20 queries/tier (n=100 total, high power)
4. Variable count (more for complex tiers)

### Decision
Use **10 queries per tier (50 total)** with uniform distribution.

### Rationale
**Chosen: 10/Tier (50 Total)**
- **Statistical power**: n=50 achieves 80% power (α=0.05, d=0.8)
- **Manageable**: 50 queries feasible for manual creation + expert review
- **Per-tier validity**: 10/tier sufficient for tier-level accuracy (±12% CI)
- **Balanced effort**: ~2-3 days total (creation + validation)

**Rejected: 5/Tier (25 Total)**
- Insufficient statistical power (60%)
- ±18% CI per tier (too wide)
- Risk of Type II error

**Rejected: 20/Tier (100 Total)**
- Diminishing returns (85% power vs 80%)
- 2x effort for minimal gain
- Ground truth validation bottleneck

**Rejected: Variable Count**
- Complicates statistical analysis
- No strong rationale for imbalance
- Less comparable across tiers

### Consequences
- ✅ 80% statistical power achieved
- ✅ Feasible effort (2-3 days)
- ✅ ±12% confidence intervals per tier
- ⚠️ Tier-level CIs wider than overall (acceptable trade-off)
- ⚠️ May need expansion if initial results inconclusive

### Compliance
**Evidence**: Power analysis in hypothesis.md (α=0.05, power=0.80, d=0.8)
**Trade-offs**: Power vs effort - balanced at n=50

---

## ADR-021-007: Complexity Scoring Weights

### Status
**ACCEPTED** - 2025-10-16

### Context
Need to weight factors for 0-100 complexity score. Options:
1. Equal weights (20% each for 5 factors)
2. Reasoning-dominant (50% reasoning steps, 12.5% others)
3. Balanced distribution (30%, 25%, 20%, 15%, 10%)
4. Data-driven (learn from manual scoring)

### Decision
Use **balanced weight distribution**: Reasoning steps (30%), Tool invocations (25%), Data scope (20%), Aggregations (15%), Novel inference (10%).

### Rationale
**Chosen: Balanced Distribution**
- **Reasoning prioritized**: Most important factor (30%)
- **Tool complexity**: Second priority (25%) - multi-tool harder
- **Data scope**: Significant (20%) - all wells harder than one
- **Aggregations**: Moderate (15%) - statistics add complexity
- **Novel inference**: Lower (10%) - binary flag, not continuous
- **Literature-aligned**: Chen et al. EMNLP 2022 similar weights

**Rejected: Equal Weights**
- Ignores domain knowledge (reasoning more important)
- Less discriminative
- Not supported by literature

**Rejected: Reasoning-Dominant**
- Over-emphasizes one factor
- Under-values tool orchestration
- Too coarse

**Rejected: Data-Driven**
- Requires training set (chicken-egg problem)
- More complex implementation
- Not justified for 50-query dataset

### Consequences
- ✅ Interpretable weights based on domain knowledge
- ✅ Literature-aligned scoring
- ✅ Discriminative across tiers
- ⚠️ May require calibration if correlation < 0.90
- ⚠️ Weights not learned from data (acceptable for POC)

### Compliance
**Evidence**: E-021-006 (Chen et al. query complexity weights)
**Trade-offs**: Simplicity vs data-driven - chose simplicity for POC

---

## Summary Table

| ADR | Decision | Rationale | Evidence |
|-----|----------|-----------|----------|
| **ADR-021-001** | 5-tier framework | Balance granularity vs simplicity | E-021-006 |
| **ADR-021-002** | Hybrid ground truth | DB + aggregation + expert | E-021-005, E-021-007 |
| **ADR-021-003** | Multi-method authenticity | Static + runtime + differential | E-021-004 |
| **ADR-021-004** | 7-category failures | Actionable, comprehensive | E-021-001, E-021-008 |
| **ADR-021-005** | 0.80 semantic similarity | Literature-validated balance | E-021-007 |
| **ADR-021-006** | 10 queries/tier (50 total) | Statistical power + feasibility | Power analysis |
| **ADR-021-007** | Balanced complexity weights | Domain-informed, literature-aligned | E-021-006 |

---

**ADR Status**: All 7 decisions finalized
**Protocol Compliance**: SCA Full Protocol v12.2
**Last Updated**: 2025-10-16
