# Hypothesis: Retrospective Quality Score Remediation

## Task ID
020-retrospective-quality-remediation

## Overview
Systematically remediate quality scores across all 21 completed tasks by generating missing QA artifacts, defining Critical Paths, implementing test coverage, and completing context documentation.

## Problem Statement
Retrospective evaluation of tasks 001-019 revealed systematic quality gaps:
- **0% tasks** have defined Critical Path files
- **0% CP coverage** across all tasks
- **0% pass rate** for coverage, TDD, complexity, documentation, hygiene, and DCI gates
- **21/21 tasks** missing core QA artifacts (lizard, coverage, bandit, secrets)
- **47.6% context accuracy** (target: 100%)
- **Average score: 46.2/100** across all tasks

Despite these gaps, **100% authenticity** and **0 fabrication indicators** demonstrate genuine implementations that need proper validation infrastructure.

## Hypotheses

### H1: QA Artifact Generation Completeness
**Statement**: Automated generation of QA artifacts (coverage.xml, lizard_report.txt, bandit.json, secrets.baseline) achieves ≥95% successful completion rate across all 21 tasks.

**Metrics**:
- **Primary**: Artifact generation success rate (target: ≥95%)
- **Secondary**: Artifact validity (parseable, non-empty)
- **α (significance)**: 0.05

**Validation Method**:
- Execute QA suite on all 21 tasks
- Parse and validate each artifact
- Calculate success rate: (tasks_with_valid_artifacts / 21) × 100

**Thresholds**:
- ✅ Success: ≥95% (20/21 tasks)
- ⚠️ Marginal: 80-94% (17-19 tasks)
- ❌ Failure: <80% (<17 tasks)

**Baseline**: Current state = 0% (0/21 tasks have complete QA artifacts)

### H2: Critical Path Coverage Achievement
**Statement**: Post-remediation, ≥80% of tasks (17/21) achieve ≥95% Critical Path test coverage.

**Metrics**:
- **Primary**: Percentage of tasks with CP coverage ≥95%
- **Secondary**: Average CP coverage across all tasks
- **α (significance)**: 0.05

**Validation Method**:
- Define CP for each task (via cp_paths.json or hypothesis.md)
- Run pytest with coverage on CP files
- Calculate: tasks_meeting_threshold / 21

**Thresholds**:
- ✅ Success: ≥80% tasks (17/21) at ≥95% CP coverage
- ⚠️ Marginal: 60-79% tasks (13-16/21)
- ❌ Failure: <60% tasks (<13/21)

**Baseline**: Current = 0% tasks with ≥95% CP coverage

### H3: Gate Pass Rate Improvement
**Statement**: Remediation improves average gate pass rates from 24.7% to ≥70% across all 9 gates.

**Metrics**:
- **Primary**: Average gate pass rate across 9 gates
- **Secondary**: Per-gate pass rates
- **α (significance)**: 0.05

**Validation Method**:
- Re-run retrospective evaluation post-remediation
- Calculate: Σ(gate_pass_rates) / 9
- Compare to baseline: 24.7%

**Thresholds**:
- ✅ Success: ≥70% average gate pass rate
- ⚠️ Marginal: 50-69%
- ❌ Failure: <50%

**Baseline Breakdown** (from evaluation):
- Context: 72.2% ✅
- Security: 100% ✅
- Authenticity: 100% ✅
- Coverage: 0% ❌
- TDD: 0% ❌
- Complexity: 0% ❌
- Documentation: 0% ❌
- Hygiene: 0% ❌
- DCI: 0% ❌
- **Average**: 24.7%

## Critical Path
[CP]
This task's Critical Path consists of:
1. **scripts/qa_artifact_generator.py** - Automated QA artifact generation
2. **scripts/cp_definer.py** - Critical Path identification and documentation
3. **scripts/coverage_enforcer.py** - Test coverage gap analysis and enforcement
4. **scripts/context_completer.py** - Context documentation completion
5. **tests/test_qa_generator.py** - Validation of artifact generation
6. **tests/test_cp_definer.py** - Validation of CP identification
[/CP]

**Coverage Target**: ≥95% line and branch coverage on all 6 CP files

## Scope

### In-Scope
1. **QA Artifact Generation** (Priority 1)
   - Generate coverage.xml for all tasks with tests
   - Generate lizard_report.txt for all tasks with code
   - Generate bandit.json security scans
   - Generate secrets.baseline files
   - Create run_log.txt templates

2. **Critical Path Definition** (Priority 1)
   - Analyze each task's code structure
   - Identify core algorithmic/business logic files
   - Create cp_paths.json for each task
   - Document CP rationale in hypothesis.md

3. **Test Coverage Infrastructure** (Priority 2)
   - Add pytest.mark.cp markers to existing tests
   - Create test stubs for uncovered CP files
   - Configure coverage measurement for CP-specific tracking
   - Generate coverage reports with CP breakdown

4. **Context Documentation Completion** (Priority 2)
   - Complete missing hypothesis.md files
   - Complete missing evidence.json files
   - Complete missing design.md files
   - Complete missing data_sources.json files
   - Add sha256 checksums where missing

5. **Validation & Reporting** (Priority 3)
   - Re-run retrospective evaluator
   - Generate before/after comparison report
   - Validate all hypotheses (H1, H2, H3)
   - Document quality improvement metrics

### Out-of-Scope
- Writing new functional code for tasks
- Modifying existing implementations
- Running tasks 017 and 018 (active/in-progress)
- Changing protocol or SCA framework
- Performance optimization of existing code

## Data Sources

### DS-001: Retrospective Evaluation Report
- **Source**: evaluation_reports/retrospective_v2_20251015_220746.json
- **Type**: Internal evaluation output (v2.0 evaluator)
- **Size**: 21 task evaluations, ~1223 lines JSON
- **SHA256**: (to be computed)
- **Licensing**: Internal tool output
- **PII**: No
- **Retention**: 90 days (archival report)
- **Usage**: Baseline metrics, gap identification, validation targets

### DS-002: Task Directory Structure
- **Source**: tasks/001-019 directories
- **Type**: File system metadata
- **Size**: 21 task directories, ~500 files
- **Licensing**: Project codebase
- **PII**: No
- **Retention**: Permanent (versioned)
- **Usage**: CP identification, artifact generation targets

### DS-003: Protocol Specification
- **Source**: C:\projects\Work Projects\.claude\full_protocol.md
- **Type**: Specification document
- **Licensing**: Internal protocol
- **PII**: No
- **Retention**: Permanent
- **Usage**: Gate definitions, QA requirements, compliance standards

## Success Criteria

### Must-Have (Phase Exit Gates)
1. ✅ H1 validated: ≥95% artifact generation success
2. ✅ H2 validated: ≥80% tasks achieve ≥95% CP coverage
3. ✅ H3 validated: ≥70% average gate pass rate
4. ✅ All tasks have cp_paths.json or CP marked in hypothesis.md
5. ✅ Re-evaluation shows measurable improvement (≥30% score increase)
6. ✅ Zero fabrication indicators maintained
7. ✅ TDD Guard passes for all new test files
8. ✅ This task achieves 95%+ CP coverage

### Nice-to-Have
- Documentation coverage ≥95% on new scripts
- Complexity CCN ≤10 on all new code
- Integration with CI/CD for automated QA runs
- Dashboard for quality metrics tracking

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Tasks lack testable code | Medium | High | Create test infrastructure, document gaps |
| CP identification ambiguous | High | Medium | Use heuristics: src/core, src/models, algorithms |
| Test execution failures | Medium | High | Skip failing tasks, document blockers |
| Artifact parsing errors | Low | Medium | Validate artifacts, log errors, retry |
| Coverage inflation | Low | High | Audit CP definitions, require justification |
| Time overrun | Medium | Medium | Prioritize P1 items, defer P3 if needed |

## Constraints & Assumptions

### Constraints
- **No code modification**: Only add QA infrastructure, don't change implementations
- **No execution of 017/018**: These tasks are active/in-progress
- **Deterministic**: All artifact generation must be reproducible
- **Non-destructive**: Preserve all existing artifacts and code

### Assumptions
1. Tasks 001-016, 019 are stable and not under active development
2. Existing tests are valid and can run without modification
3. Python environment has all required dependencies (pytest, coverage, lizard, bandit, detect-secrets)
4. Critical Path can be inferred from code structure when not documented
5. Test stubs are acceptable for initial coverage (to be filled later)

## Exclusions
- Not updating task 017 (in phase 2, ok status)
- Not updating task 018 (in phase 2, in_progress status)
- Not retroactively modifying completed task deliverables
- Not implementing new features or fixing bugs in existing tasks
- Not changing the SCA protocol or evaluation criteria

## Dependencies
- **Tool Dependencies**: pytest, pytest-cov, lizard, bandit, detect-secrets, mypy
- **Task Dependencies**: None (independent meta-task)
- **Data Dependencies**: Retrospective evaluation report (DS-001)

## Estimated Effort
- **Phase 0** (Context): 1 hour (current phase)
- **Phase 1** (Data & CP Definition): 3 hours
- **Phase 2** (Design & Tooling): 2 hours
- **Phase 3** (Implementation): 6 hours
- **Phase 4** (Validation & Reporting): 2 hours
- **Phase 5** (Documentation): 1 hour
- **Total**: 15 hours

## Validation Plan

### Phase 3 Validation (Per-Task QA)
For each task (001-016, 019):
1. Verify all 4 QA artifacts exist and are parseable
2. Verify cp_paths.json exists OR CP marked in hypothesis.md
3. Verify coverage.xml includes CP files (if code exists)
4. Verify no new fabrication indicators introduced

### Phase 4 Validation (Aggregate Metrics)
1. Re-run retrospective evaluator
2. Compare before/after gate pass rates
3. Validate H1, H2, H3 against thresholds
4. Generate statistical summary (mean, median, std dev of scores)

### Phase 5 Validation (Deliverables)
1. Verify final report includes all required sections
2. Verify before/after comparison charts/tables
3. Verify recommendations for remaining gaps
4. Verify this task's own QA gates pass

## Tags
#meta-task #quality-remediation #qa-infrastructure #retrospective #v12.0
