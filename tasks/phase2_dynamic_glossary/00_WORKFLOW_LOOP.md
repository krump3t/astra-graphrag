# Phase 2 Dynamic Glossary Enhancement - Workflow Loop

**Protocol**: Scientific Coding Agent v9.0
**Phase**: Phase 2 - Dynamic Glossary Enhancement
**Date**: 2025-10-14

---

## Workflow Loop Overview

This document defines the **scientific workflow loop** for implementing the dynamic glossary enhancement, following the methodology specified in user memory instructions.

---

## The 5-Phase Workflow Loop

### Phase 1: Discovery and Research ✅ COMPLETE

**Objective**: Define the problem and synthesize the current state-of-the-art

**Deliverables**:
- ✅ Problem Specification: Static glossary (15 terms) → Dynamic glossary (unlimited via web scraping)
- ✅ Research Synthesis: Identified trusted sources (SLB, SPE, AAPG, SEG, EIA)
- ✅ Justified Technical Approach: BeautifulSoup for scraping + Redis for caching
- ✅ Authenticity Assessment: Differential testing required to prove real web scraping

**Evidence**: `E2E_VALIDATION_REPORT.md`, `PHASE1_AUTHENTICITY_VERIFICATION.md`

---

### Phase 2: Design and Experimental Framework

**Objective**: Formulate a robust solution design and define the verification strategy

**Tasks**:
1. **Solution Architecture** (2-3 hours)
   - Design web scraping architecture
   - Define scraper interface (abstract base class)
   - Design fallback strategy (trusted sources → broader web)
   - Handle rate limiting and retries

2. **Reproducibility Strategy**
   - Document dependencies (beautifulsoup4, redis, requests)
   - Define environment variables for API keys/endpoints
   - Create requirements.txt entry

3. **Verification Strategy (The Hypothesis)**
   - Define TDD approach: Write tests BEFORE scrapers
   - Plan differential tests: Scraped content ≠ static content
   - Plan authenticity tests: Multiple sources → different results
   - Plan error handling tests: Network failures, malformed HTML

4. **Quality Assurance Toolchain**
   - pytest: Unit testing
   - responses/httpretty: HTTP mocking
   - fakeredis: Redis mocking
   - mypy: Type checking
   - bandit: Security scanning

**Deliverables**:
- [ ] `01_SOLUTION_DESIGN.md` - Architecture and scraper designs
- [ ] `02_VERIFICATION_STRATEGY.md` - Test plan and success criteria
- [ ] `03_SCRAPER_INTERFACE.py` - Abstract base class design

---

### Phase 3: Implementation (The Experiment)

**Objective**: Execute the design in a reproducible environment using TDD

**TDD Workflow**:

#### Step 3.1: Setup Environment
```bash
pip install beautifulsoup4 redis requests responses fakeredis
```

#### Step 3.2: Red (Write Failing Tests)
**Task**: Create `tests/unit/test_glossary_scraper.py` BEFORE implementation

**Test Cases** (15-20 tests):
1. SLB scraper extracts known term (NPHI)
2. SPE scraper extracts known term (GR)
3. AAPG scraper extracts known term (ROP)
4. Scraper handles unknown term gracefully
5. Scraper handles network timeout
6. Scraper handles malformed HTML
7. Scraper handles 404 response
8. Scraper handles rate limiting (429)
9. Cache stores definition correctly
10. Cache retrieves definition within TTL
11. Cache expires after TTL
12. Cache handles Redis connection failure
13. Differential: SLB result ≠ SPE result for same term
14. Differential: Scraped ≠ static for overlapping terms
15. Differential: Multiple scrapes of same term → identical

**Expected**: All tests FAIL (no implementation yet)

#### Step 3.3: Green (Implement to Pass Tests)
**Task**: Create implementation files

**Files to Create**:
1. `services/mcp/glossary_scraper.py` - Scraper implementations
2. `services/mcp/glossary_cache.py` - Redis caching layer
3. `services/mcp/scraper_factory.py` - Factory for scraper selection

**Implementation Order**:
1. Abstract base class (`GlossaryScraper`)
2. SLB scraper (simplest)
3. Cache layer (Redis)
4. Additional scrapers (SPE, AAPG)
5. Orchestrator (try sources in priority order)

**Expected**: All tests PASS

#### Step 3.4: Refactor (Optimize and Clean)
**Task**: Improve code quality while maintaining test pass

**Refactoring Targets**:
- Extract common HTML parsing logic
- Add retry logic with exponential backoff
- Optimize cache key generation
- Add comprehensive docstrings
- Verify type hints complete

**Expected**: All tests STILL PASS + complexity low

#### Step 3.5: Integrate into MCP
**Task**: Update `mcp_server.py` to use dynamic scraper

**Changes**:
```python
# OLD (mcp_server.py:237-285)
def get_dynamic_definition(term: str) -> Dict[str, Any]:
    # Uses static STATIC_GLOSSARY

# NEW (mcp_server.py:237-285)
def get_dynamic_definition(term: str) -> Dict[str, Any]:
    # 1. Check Redis cache
    # 2. Try scrapers (SLB → SPE → AAPG)
    # 3. Fallback to static glossary
    # 4. Cache result in Redis
```

**Deliverables**:
- [ ] `tests/unit/test_glossary_scraper.py` - Test suite
- [ ] `services/mcp/glossary_scraper.py` - Scraper implementations
- [ ] `services/mcp/glossary_cache.py` - Redis caching
- [ ] Updated `mcp_server.py` - Integration

---

### Phase 4: Analysis and Validation

**Objective**: Rigorously verify the implementation against quality standards

**Tasks**:

#### 4.1: Automated Analysis
```bash
# Type checking
mypy services/mcp/glossary_scraper.py --strict

# Security scanning
bandit services/mcp/glossary_scraper.py -r

# Dependency vulnerabilities
pip-audit

# Test execution
pytest tests/unit/test_glossary_scraper.py -v --cov=services/mcp
```

#### 4.2: Authenticity Validation
**Task**: Create `tests/validation/test_glossary_authenticity.py`

**Differential Tests** (5-7 tests):
1. **Scraped ≠ Static**: Prove definitions come from web, not static dict
2. **Source Diversity**: SLB result ≠ SPE result ≠ AAPG result
3. **Cache Timing**: Cached result identical to fresh scrape (within TTL)
4. **Parameter Processing**: Different terms → different results
5. **Real HTTP**: Network calls actually made (mock verification)
6. **Honest Failure**: 404 → genuine error, not fake response
7. **Determinism**: Same term → same result (idempotent)

#### 4.3: Quality Gate Verification
**Requirements**:
- ✅ Authenticity: 100% differential test pass
- ✅ Correctness: 100% unit test pass
- ✅ Type Safety: 0 mypy errors (strict)
- ✅ Security: 0 critical/high bandit findings
- ✅ Test Coverage: ≥90% line coverage
- ✅ Complexity: All functions CCN <15
- ✅ Performance: Scrape time <2s per term

**Deliverables**:
- [ ] `tests/validation/test_glossary_authenticity.py` - Differential tests
- [ ] `PHASE2_VALIDATION_REPORT.md` - Quality gate results
- [ ] Test coverage report (HTML)

---

### Phase 5: Conclusion and Scientific Reporting

**Objective**: Document the process, findings, and reproducibility

**Report Structure** (following scientific paper format):

#### 5.1: Abstract
- Summary of task, methodology, outcome
- Key metrics: Terms supported, scrape time, cache hit rate

#### 5.2: Introduction
- Problem: Static glossary limited to 15 terms
- Solution: Dynamic web scraping from trusted sources

#### 5.3: Literature Review
- Web scraping best practices
- Rate limiting strategies
- Caching patterns (Redis TTL)

#### 5.4: Methodology
- TDD approach (Red-Green-Refactor)
- Scraper architecture (Factory pattern)
- Cache design (Redis with 15-min TTL)

#### 5.5: Results and Analysis
- **Quality Metrics**: Test pass rate, coverage, complexity
- **Authenticity Proof**: Differential test results
- **Performance**: Scrape times, cache hit rates

#### 5.6: Discussion
- Strengths: Unlimited terms, trusted sources, fast caching
- Limitations: Rate limits, network dependency
- Future work: Add more sources, improve parsing

#### 5.7: Reproducibility
- Environment setup instructions
- Test execution commands
- Expected outputs

#### 5.8: Conclusion
- Summary of achievements
- Production readiness assessment

**Deliverables**:
- [ ] `PHASE2_CAPABILITY_REPORT.md` - Scientific report

---

## Workflow Loop Iteration Points

### When to Loop Back

**Loop to Phase 1** if:
- Research reveals better approach (e.g., API instead of scraping)
- Trusted sources unavailable/blocked

**Loop to Phase 2** if:
- Design doesn't meet quality gates
- Architecture needs revision

**Loop to Phase 3** if:
- Tests reveal implementation bugs
- Performance unacceptable (<2s threshold)

**Loop to Phase 4** if:
- Quality gates fail
- Authenticity not proven

---

## Current Status

**Phase 1**: ✅ COMPLETE (E2E validation, authenticity verification)
**Phase 2**: ⏳ IN PROGRESS (next task)
**Phase 3**: ⏸️ PENDING
**Phase 4**: ⏸️ PENDING
**Phase 5**: ⏸️ PENDING

---

## Success Criteria

### Phase 2 Complete When:
- [ ] Solution architecture documented
- [ ] Scraper interface designed
- [ ] Test plan created with 15+ test cases
- [ ] Verification strategy defined
- [ ] Quality assurance toolchain prepared

### Phase 3 Complete When:
- [ ] All tests written (Red)
- [ ] All implementations created (Green)
- [ ] All tests pass (100%)
- [ ] Code refactored (CCN <15)
- [ ] MCP tool integrated

### Phase 4 Complete When:
- [ ] All quality gates pass
- [ ] Differential tests validate authenticity
- [ ] Performance meets <2s threshold
- [ ] Security scan clean

### Phase 5 Complete When:
- [ ] Scientific report complete
- [ ] Reproducibility instructions tested
- [ ] Demo successfully executed

---

## Next Action

**Immediate Task**: Begin Phase 2 - Design and Experimental Framework

**Steps**:
1. Create `01_SOLUTION_DESIGN.md`
2. Design scraper architecture
3. Define scraper interface
4. Document fallback strategy
5. Plan rate limiting approach

**Estimated Time**: 2-3 hours

---

**Document Created**: 2025-10-14
**Current Phase**: Transition Phase 1 → Phase 2
**Next Deliverable**: `01_SOLUTION_DESIGN.md`
