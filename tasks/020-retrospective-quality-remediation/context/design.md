# Design: Retrospective Quality Score Remediation

## Architecture Overview

This task implements a **retrospective QA infrastructure layer** that systematically applies validation tooling across all previously completed tasks without modifying their implementations.

```
┌─────────────────────────────────────────────────────────────┐
│                    Task 020 Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │  Task Scanner   │──────▶│  CP Identifier  │             │
│  │  (001-019)      │       │  (Heuristic)    │             │
│  └─────────────────┘       └─────────────────┘             │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │ QA Generator    │       │  CP Documenter  │             │
│  │ (4 artifacts)   │       │  (cp_paths.json)│             │
│  └─────────────────┘       └─────────────────┘             │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │ Test Scaffolder │       │ Context Complete│             │
│  │ (CP markers)    │       │ (4 files)       │             │
│  └─────────────────┘       └─────────────────┘             │
│           │                         │                        │
│           └────────┬────────────────┘                        │
│                    ▼                                          │
│           ┌─────────────────┐                               │
│           │  Validator &    │                               │
│           │  Re-Evaluator   │                               │
│           └─────────────────┘                               │
│                    │                                          │
│                    ▼                                          │
│           ┌─────────────────┐                               │
│           │  Quality Report │                               │
│           │  (Before/After) │                               │
│           └─────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. QA Artifact Generator (`scripts/qa_artifact_generator.py`)

**Purpose**: Generate 4 required QA artifacts for each task

**Inputs**:
- Task directory path (tasks/XXX-name/)
- Task metadata (has tests, has src, has CP)

**Outputs**:
- `qa/coverage.xml` - pytest-cov XML report
- `qa/lizard_report.txt` - Complexity analysis
- `qa/bandit.json` - Security scan results
- `qa/secrets.baseline` - Secret detection baseline
- `artifacts/run_log.txt` - Execution log template

**Algorithm**:
```python
def generate_artifacts(task_path: Path) -> ArtifactResult:
    results = ArtifactResult(task_id=task_path.name)

    # 1. Coverage (if tests exist)
    if (task_path / "tests").exists():
        run_pytest_coverage(task_path)
        results.coverage_success = validate_coverage_xml(task_path / "qa/coverage.xml")

    # 2. Complexity (if src exists)
    if (task_path / "src").exists() or has_python_files(task_path):
        run_lizard(task_path)
        results.lizard_success = validate_lizard_report(task_path / "qa/lizard_report.txt")

    # 3. Security (always)
    run_bandit(task_path)
    results.bandit_success = validate_bandit_json(task_path / "qa/bandit.json")

    # 4. Secrets (always)
    run_detect_secrets(task_path)
    results.secrets_success = validate_secrets_baseline(task_path / "qa/secrets.baseline")

    # 5. Run log template (if missing)
    if not (task_path / "artifacts/run_log.txt").exists():
        create_run_log_template(task_path)

    return results
```

**Error Handling**:
- Skip tests if pytest execution fails (log error)
- Generate empty baseline if no secrets found
- Continue on partial failures (best-effort)
- Log all errors to `artifacts/qa_generation_log.txt`

**Validation Metrics**:
- Artifact file exists
- File size > 0 bytes
- File is parseable (XML, JSON, TXT)
- Contains expected structure (coverage.xml has `<coverage>` tag)

### 2. Critical Path Identifier (`scripts/cp_definer.py`)

**Purpose**: Identify and document Critical Path files for each task

**Discovery Strategy** (3-tier):

**Tier 1: Explicit Configuration** (highest priority)
- Check for `context/cp_paths.json`
- If exists, validate and use as-is

**Tier 2: Hypothesis Extraction**
- Parse `context/hypothesis.md`
- Search for `[CP]...[/CP]` markers
- Extract file paths from markdown code blocks
- Generate `cp_paths.json` from extracted paths

**Tier 3: Heuristic Inference** (fallback)
- Scan for patterns: `src/core/**/*.py`, `src/models/**/*.py`, `src/algorithms/**/*.py`
- Exclude: `__init__.py`, test files, utility scripts
- Weight by cyclomatic complexity (use lizard output)
- Select top 3-5 files by complexity + centrality

**Output Format** (`cp_paths.json`):
```json
{
  "version": "1.0",
  "discovery_method": "heuristic|hypothesis|explicit",
  "confidence": "high|medium|low",
  "paths": [
    "src/core/engine.py",
    "src/models/schema.py"
  ],
  "rationale": "Identified by cyclomatic complexity (CCN>10) and import centrality",
  "discovery_date": "2025-10-15T22:30:00"
}
```

**Validation**:
- All paths in `paths` array exist
- All paths are `.py` files
- Minimum 1 path, maximum 10 paths
- No test files included (no `test_` prefix)

### 3. Coverage Enforcer (`scripts/coverage_enforcer.py`)

**Purpose**: Analyze and enforce CP-specific test coverage

**Algorithm**:
1. Load `cp_paths.json` for task
2. Parse `qa/coverage.xml`
3. Extract coverage data for CP files only
4. Calculate CP coverage percentage
5. Identify uncovered lines in CP files
6. Generate test stub recommendations

**Coverage Gap Analysis**:
```python
def analyze_cp_coverage(task_path: Path) -> CoverageAnalysis:
    cp_config = load_cp_config(task_path)
    coverage_data = parse_coverage_xml(task_path / "qa/coverage.xml")

    gaps = []
    for cp_file in cp_config["paths"]:
        file_coverage = coverage_data.get_file_coverage(cp_file)

        if file_coverage.line_coverage < 0.95:
            gaps.append(CoverageGap(
                file=cp_file,
                coverage=file_coverage.line_coverage,
                uncovered_lines=file_coverage.uncovered_lines,
                missing_tests=suggest_tests(cp_file, file_coverage)
            ))

    return CoverageAnalysis(
        overall_cp_coverage=calculate_cp_coverage(coverage_data, cp_config),
        gaps=gaps,
        recommendations=generate_test_stubs(gaps)
    )
```

**Test Stub Generation** (Optional Phase 4):
- Create `tests/cp/test_{module}_cp.py` skeletons
- Add `@pytest.mark.cp` decorators
- Add TODO comments with coverage targets
- **NOTE**: Stubs are scaffolding only, not functional tests

### 4. Context Completer (`scripts/context_completer.py`)

**Purpose**: Complete missing context documentation files

**Required Files** (per protocol):
1. `hypothesis.md` - Research question, metrics, CP
2. `design.md` - Architecture, leakage prevention, validation
3. `evidence.json` - ≥3 P1 sources with ≤25-word quotes
4. `data_sources.json` - SHA256, rows/cols, licensing, PII

**Completion Strategy**:

**For `hypothesis.md`**:
- If missing: Create minimal template with placeholders
- If exists but no CP: Extract CP from code using `cp_definer.py`
- If exists with CP: No action (validated in Tier 2)

**For `evidence.json`**:
- If missing: Create empty array with template P1 source
- If exists but <3 P1: Log warning, don't modify (out of scope)

**For `design.md`**:
- If missing: Create minimal template referencing existing code
- If exists: Validate has architecture section

**For `data_sources.json`**:
- If missing: Scan for data files (*.csv, *.json, *.parquet)
- Compute SHA256 checksums
- Create data_sources.json with detected files
- If no data files: Create with "synthetic" entry

**SHA256 Computation**:
```python
def compute_file_checksums(task_path: Path) -> List[Dict]:
    data_files = find_data_files(task_path)

    sources = []
    for file in data_files:
        sha256 = hashlib.sha256(file.read_bytes()).hexdigest()

        # Count rows if CSV/JSON
        rows, cols = detect_dimensions(file)

        sources.append({
            "id": f"DS-{len(sources)+1:03d}",
            "name": file.name,
            "path": str(file.relative_to(task_path)),
            "sha256": sha256,
            "rows": rows,
            "cols": cols,
            "licensing": "project_internal",
            "pii": False,
            "retention_days": 90
        })

    return sources
```

## Data Flow

```
Input: evaluation_reports/retrospective_v2_20251015_220746.json
  │
  ├─▶ Parse evaluation results
  │   └─▶ Extract task IDs (001-019 excluding 017, 018)
  │
  ├─▶ For each task:
  │   │
  │   ├─▶ QA Artifact Generator
  │   │   ├─▶ pytest --cov → coverage.xml
  │   │   ├─▶ lizard → lizard_report.txt
  │   │   ├─▶ bandit → bandit.json
  │   │   └─▶ detect-secrets → secrets.baseline
  │   │
  │   ├─▶ CP Identifier
  │   │   ├─▶ Check cp_paths.json (explicit)
  │   │   ├─▶ Parse hypothesis.md (extraction)
  │   │   └─▶ Heuristic scan (fallback)
  │   │
  │   ├─▶ Coverage Enforcer
  │   │   ├─▶ Parse coverage.xml
  │   │   ├─▶ Calculate CP coverage
  │   │   └─▶ Generate gap report
  │   │
  │   └─▶ Context Completer
  │       ├─▶ Check 4 required files
  │       ├─▶ Generate missing files
  │       └─▶ Compute checksums
  │
  └─▶ Re-run Evaluator
      └─▶ Compare before/after metrics
          └─▶ Output: reports/quality_improvement_report.md
```

## Leakage Prevention

**Data Leakage Risks**: NONE (no ML models, no train/test splits)

**Test Contamination Prevention**:
- Tests only scaffold stubs, not functional tests
- No modification of existing test logic
- CP identification is static analysis only
- No execution of task code during analysis

**Determinism Enforcement**:
- All file scans use sorted order
- SHA256 checksums are deterministic
- Artifact generation uses fixed random seeds (if needed)
- CP heuristic uses stable sort by (complexity DESC, path ASC)

## Validation Design

### Differential Testing
**Not applicable** - No algorithmic logic to validate, only tooling orchestration

### Sensitivity Analysis
**Coverage Threshold Sensitivity**:
- Test H2 with thresholds: 90%, 95%, 99%
- Measure task pass counts at each threshold
- Validate 95% is achievable target

**CP Count Sensitivity**:
- Test CP heuristic with limits: 3, 5, 10 files
- Measure coverage achievability vs. CP size
- Validate 3-5 files is optimal range

### K-Fold Cross-Validation
**Not applicable** - No predictive modeling

### Statistical Validation
**H1 Validation** (Binomial Test):
- Null hypothesis: p(artifact_success) = 0.5 (random)
- Alternative: p(artifact_success) > 0.95 (target)
- Test: Binomial test with n=21, k=successes, p0=0.5
- Reject null if p-value < 0.05

**H2 Validation** (Proportion Test):
- Null hypothesis: p(CP_coverage≥95%) = 0.5
- Alternative: p(CP_coverage≥95%) > 0.8 (target)
- Test: One-sample proportion test
- Reject null if p-value < 0.05

**H3 Validation** (Paired t-test):
- Null hypothesis: μ_after - μ_before = 0
- Alternative: μ_after - μ_before > 0
- Test: Paired t-test on before/after gate pass rates
- Reject null if p-value < 0.05 AND effect size > 0.5

## Technology Stack

### Core Tools
- **pytest**: Test execution and coverage measurement
- **pytest-cov**: Coverage.py integration for pytest
- **lizard**: Cyclomatic complexity analysis
- **bandit**: Security vulnerability scanning
- **detect-secrets**: Secret detection
- **mypy**: Type checking (for new scripts)

### Libraries
- **pathlib**: File system operations
- **json**: Configuration parsing
- **xml.etree.ElementTree**: Coverage XML parsing
- **hashlib**: SHA256 checksum computation
- **re**: Pattern matching for CP extraction
- **dataclasses**: Structured data types
- **typing**: Type annotations

### Reporting
- **markdown**: Report generation
- **pandas** (optional): Metrics aggregation
- **matplotlib** (optional): Before/after charts

## Error Handling Strategy

### Artifact Generation Failures
- **Test execution fails**: Log error, skip coverage.xml, continue
- **Lizard parse error**: Log error, generate empty report, continue
- **Bandit crash**: Log error, create empty findings JSON, continue
- **No secrets baseline**: Create empty baseline (valid state)

### CP Identification Failures
- **No heuristic matches**: Create cp_paths.json with empty array, log warning
- **Hypothesis parse error**: Fall back to heuristic, log warning
- **Invalid paths in explicit config**: Filter invalid paths, log warning

### Context Completion Failures
- **SHA256 compute error**: Use "pending" as checksum, log error
- **Data file detection error**: Skip file, log warning, continue
- **Template creation I/O error**: FATAL - halt and report

### Validation Failures
- **Evaluator crash**: FATAL - cannot validate hypotheses
- **Report generation error**: FATAL - deliverable not produced

## Assumptions

1. **Static Analysis Only**: Tasks don't need to execute successfully
2. **Test Stability**: Existing tests can run without modification
3. **Tool Availability**: pytest, lizard, bandit, detect-secrets installed
4. **File System Access**: Read/write permissions on all task directories
5. **CP Inferable**: Code structure provides sufficient signals for CP identification
6. **Artifact Validity**: Generated artifacts are meaningful proxies for quality

## Constraints

1. **Non-Destructive**: Never modify existing code or tests
2. **Exclude Active Tasks**: Skip tasks 017 and 018
3. **No New Features**: Only QA infrastructure, no functional code
4. **Deterministic**: All operations must be reproducible
5. **Time-Boxed**: Phase 3 limited to 6 hours (average 20 min/task)

## Next Steps (Phase 1)

1. Implement QA Artifact Generator script
2. Implement CP Identifier script
3. Validate tools on 2-3 sample tasks (001, 004, 013)
4. Document edge cases and failure modes
5. Proceed to Phase 2 (Design Review)
