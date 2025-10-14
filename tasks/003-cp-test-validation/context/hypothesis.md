# Core Hypothesis - Task 003: CP Test Validation & TDD Compliance

**Capability to prove**: The Critical Path test suites authentically validate functional components through proper TDD methodology, with task-specific, code-specific, and domain-specific requirements fully incorporated before demo rehearsal.

## Measurable Metrics

1. **CP Coverage**: ≥95% line coverage, ≥85% branch coverage for all Critical Path components (α = 0.05)
2. **TDD Compliance**: 100% of CP tests written before/alongside implementation, validated by git history or test timestamps
3. **Domain Specificity**: ≥90% of CP tests include domain-specific validation (petroleum engineering terms, well log patterns, LAS format compliance)
4. **Code Specificity**: 100% of CP tests validate actual implementation details (not generic behavior)
5. **Authenticity**: 100% of CP tests use real computation (0 mocked responses in differential/sensitivity tests)

## Critical Path (Minimum to Prove It)

1. **Coverage Analysis** (`scripts/validation/validate_cp_coverage.py`):
   - Measure line/branch coverage for CP components
   - Identify untested critical paths
   - Generate coverage gap report

2. **TDD Methodology Audit** (`scripts/validation/audit_tdd_compliance.py`):
   - Verify tests written before/with implementation
   - Check test-first commit patterns in git history
   - Validate test timestamps vs implementation timestamps

3. **Domain Specificity Validator** (`scripts/validation/validate_domain_specificity.py`):
   - Scan test code for petroleum engineering domain terms
   - Verify LAS format validation (DEPT, GR, NPHI, etc.)
   - Check for domain-specific assertions (porosity, permeability, resistivity)

4. **Code Specificity Validator** (`scripts/validation/validate_code_specificity.py`):
   - Detect generic test patterns (assertEqual(True, True))
   - Verify tests reference actual implementation details
   - Check for placeholder/stub detection

5. **Authenticity Validator** (`scripts/validation/validate_authenticity.py`):
   - Scan for mock usage in differential/sensitivity tests
   - Verify real HTTP calls (no mocked requests)
   - Check for hardcoded response detection

## Explicit Exclusions

- ❌ Unit test validation (out of scope - focusing on CP tests only)
- ❌ Integration test infrastructure setup
- ❌ Performance benchmarking
- ❌ Mutation testing implementation
- ❌ Test data generation

## Validation Plan (Brief)

### Statistical Tests
- **Chi-square test** (domain term frequency): H0: term frequency ≤ 10%, H1: term frequency > 10%, α = 0.05
- **Binomial test** (TDD compliance): H0: compliance < 100%, H1: compliance = 100%, α = 0.05

### Differential Testing (3 tests)
1. **Input**: Add mock to differential test → **Expected**: Validation fails, reports mock usage
2. **Input**: Remove domain term from test → **Expected**: Domain specificity score decreases
3. **Input**: Generic assertion → **Expected**: Code specificity validator flags as non-specific

### Validation Methods
- **Coverage analysis**: pytest-cov with --cov-report=html
- **Git history analysis**: git log --follow --diff-filter=A --find-renames
- **AST analysis**: Python ast module to parse test code

## Stop Conditions (What Would Falsify Success)

1. **CP coverage < 90%** for any critical component (critical failure)
2. **TDD compliance < 100%** (tests must precede/accompany implementation)
3. **Domain specificity < 80%** (tests lack petroleum engineering validation)
4. **Mocked responses found** in ≥1 differential/sensitivity test (not authentic)
5. **Generic test patterns** in ≥10% of CP tests (not code-specific)
