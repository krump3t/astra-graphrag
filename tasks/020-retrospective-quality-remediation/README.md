# Task 020: Retrospective Quality Score Remediation

## Quick Start

This meta-task systematically improves quality scores across all completed tasks (001-019) by generating missing QA artifacts and defining Critical Paths.

**Status**: Context Phase (In Progress)
**Type**: Meta-task (Quality Infrastructure)
**Duration**: 15 hours estimated

## Problem Statement

Retrospective evaluation revealed:
- **0% CP coverage** across all 21 tasks
- **21/21 tasks missing QA artifacts**
- **Average score: 46.2/100**
- **Gate pass rate: 24.7%** (target: ≥70%)

## Solution

Automated remediation pipeline:
1. Generate QA artifacts (coverage, complexity, security)
2. Define Critical Paths using 3-tier discovery
3. Implement CP-specific test coverage tracking
4. Complete missing context documentation
5. Re-evaluate and validate improvements

## Hypotheses

| ID | Hypothesis | Target | Validation |
|----|------------|--------|------------|
| H1 | Artifact generation ≥95% success | 95% | Binomial test |
| H2 | ≥80% tasks achieve ≥95% CP coverage | 80% | Proportion test |
| H3 | Average gate pass rate ≥70% | 70% | Paired t-test |

## Directory Structure

```
020-retrospective-quality-remediation/
├── context/
│   ├── hypothesis.md          # 3 testable hypotheses
│   ├── design.md              # 4-component architecture
│   ├── evidence.json          # 3 P1 + 3 P2 sources
│   ├── data_sources.json      # 3 data sources with SHA256
│   ├── cp_paths.json          # Critical Path definition
│   ├── executive_summary.md   # Executive overview
│   └── state.json             # Task state
├── scripts/
│   ├── qa_artifact_generator.py   # Generate 4 artifacts per task
│   ├── cp_definer.py              # Identify & document CPs
│   ├── coverage_enforcer.py       # CP-specific coverage
│   └── context_completer.py       # Complete missing files
├── tests/
│   ├── test_qa_generator.py       # Validate artifact generation
│   └── test_cp_definer.py         # Validate CP identification
├── qa/
│   ├── coverage.xml               # This task's coverage
│   ├── lizard_report.txt          # Complexity analysis
│   ├── bandit.json                # Security scan
│   └── secrets.baseline           # Secret detection
├── artifacts/
│   ├── state.json                 # Execution state
│   └── run_log.txt                # Command log
└── reports/
    ├── quality_improvement_report.md  # Before/after comparison
    └── validation_results.json        # Hypothesis validation
```

## Critical Path

1. **scripts/qa_artifact_generator.py** - Orchestrates artifact generation
2. **scripts/cp_definer.py** - 3-tier CP discovery (explicit → hypothesis → heuristic)
3. **scripts/coverage_enforcer.py** - CP-specific coverage measurement
4. **scripts/context_completer.py** - Completes missing context files
5. **tests/test_qa_generator.py** - Validates artifact generation
6. **tests/test_cp_definer.py** - Validates CP identification

**Coverage Target**: ≥95% line and branch coverage

## Phases

### Phase 0: Context (1 hour) ✅
- Define hypotheses with statistical validation
- Design 4-component architecture
- Document evidence and data sources

### Phase 1: Data & CP Definition (3 hours)
- Implement CP identifier (3-tier discovery)
- Define CPs for 19 tasks
- Compute SHA256 checksums

### Phase 2: Design & Tooling (2 hours)
- Implement QA artifact generator
- Implement coverage enforcer
- Implement context completer

### Phase 3: Implementation (6 hours)
- Execute artifact generation (76 artifacts)
- Generate CP coverage reports
- Complete missing context files

### Phase 4: Validation & Reporting (2 hours)
- Re-run retrospective evaluator
- Validate H1, H2, H3
- Generate quality improvement report

### Phase 5: Documentation (1 hour)
- Document lessons learned
- Create remediation playbook

## Scope

### In-Scope (19 Tasks)
- Tasks 001-016 (completed)
- Task 019 (completed)

### Out-of-Scope
- Task 017 (active, phase 2 ok)
- Task 018 (in-progress, phase 2 39%)
- Code modification (QA only)

## Key Files

- **context/hypothesis.md**: Detailed hypotheses, metrics, CP definition
- **context/design.md**: Architecture, algorithms, validation approach
- **context/executive_summary.md**: High-level overview for stakeholders
- **context/state.json**: Current task state and progress tracking

## Tools Required

- pytest, pytest-cov
- lizard (complexity)
- bandit (security)
- detect-secrets
- mypy (type checking)

## Expected Outcomes

### Deliverables
- **76 QA artifacts** (19 tasks × 4 artifacts)
- **19 CP definitions** (cp_paths.json)
- **Completed context files** (missing hypothesis/evidence/design/data_sources)
- **Quality improvement report** (before/after with statistical validation)

### Target Metrics
- Artifact generation: ≥95% success (18/19 tasks)
- CP coverage: ≥80% tasks (15/19) at ≥95%
- Gate pass rate: ≥70% average (from 24.7%)
- Average score: ≥60/100 (from 46.2/100)

## Running the Pipeline

```bash
# Phase 1: Define CPs
python scripts/cp_definer.py --tasks-dir tasks --output-dir tasks

# Phase 3: Generate artifacts
python scripts/qa_artifact_generator.py --tasks-dir tasks --exclude 017,018

# Phase 3: Enforce coverage
python scripts/coverage_enforcer.py --tasks-dir tasks --threshold 0.95

# Phase 3: Complete context
python scripts/context_completer.py --tasks-dir tasks

# Phase 4: Re-evaluate
python sca_retrospective_evaluator_v2.py --tasks-dir tasks --verbose

# Phase 4: Generate report
python scripts/generate_improvement_report.py --baseline evaluation_reports/retrospective_v2_20251015_220746.json --current evaluation_reports/retrospective_v2_[latest].json
```

## Success Criteria

✅ H1 validated: ≥95% artifact generation success
✅ H2 validated: ≥80% tasks achieve ≥95% CP coverage
✅ H3 validated: ≥70% average gate pass rate
✅ Zero fabrication indicators maintained
✅ TDD Guard passes
✅ This task achieves ≥95% CP coverage

## Contact

For questions or issues with this task, refer to:
- **Hypothesis**: context/hypothesis.md (detailed methodology)
- **Design**: context/design.md (architecture and algorithms)
- **Executive Summary**: context/executive_summary.md (high-level overview)
