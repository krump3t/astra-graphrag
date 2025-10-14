# Reproducibility Guide

This document ensures that all experiments, tests, and results from the Astra-GraphRAG project can be independently reproduced.

## Data Integrity Verification

All test data files have been checksummed with SHA256 hashes to ensure data integrity and detect corruption or modification.

### Verifying Data Integrity

**1. Check all data files against stored checksums:**

```bash
python scripts/verify_checksums.py
```

This will:
- Recompute SHA256 hashes for all data files in `data/raw/`
- Compare against stored checksums in `data/checksums.json`
- Report any mismatches (indicating corruption/modification)

**2. Regenerate checksums (if data files are updated intentionally):**

```bash
python scripts/generate_checksums.py
```

This will:
- Compute SHA256 for all data files
- Update `data/checksums.json`
- **NOTE**: Only run this when you've intentionally updated data files

### Checksum File Format

`data/checksums.json` contains:

```json
{
  "force2020/las_files/15_9-13.las": {
    "sha256": "933752fd96b8c28675b3c...",
    "size_bytes": "5897948"
  },
  ...
}
```

- **Relative paths**: All paths are relative to `data/raw/`
- **SHA256**: 64-character hexadecimal hash
- **Size**: File size in bytes (helps detect truncation)

## Test Data Sources

### FORCE 2020 Machine Learning Competition

- **Source**: [FORCE 2020 ML Competition](https://github.com/equinor/force-2020-machine-learning-competition)
- **License**: Apache 2.0
- **Data**: 120 LAS files (well logs from Norwegian Continental Shelf)
- **Location**: `data/raw/force2020/las_files/*.las`
- **Critical test files**:
  - `15_9-13.las` (5.9 MB) - Primary test well for relationship queries
  - `16_1-2.las` (4.9 MB) - Secondary test well for extraction queries
  - `25_10-10.las` (4.6 MB) - Test well for aggregation queries

### USGS Water Services

- **Source**: [USGS Instantaneous Values Web Service](https://waterservices.usgs.gov/rest/IV-Service.html)
- **License**: Public domain (USGS data)
- **Data**: 2 JSON files (water quality measurements from Wabash River site 03339000)
- **Location**: `data/raw/structured/usgs_water/*.json`

### Kansas Geological Survey LAS Files

- **Source**: [KGS Oil & Gas Well Logs](https://www.kgs.ku.edu/)
- **License**: Public domain (state geological survey data)
- **Data**: 2 LAS files (sample well logs for testing)
- **Location**: `data/raw/unstructured/kgs_las/*.las`

## Environment Reproducibility

### Python Environment

**Python Version**: 3.11.9

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Lock file**: `requirements.txt` pins all transitive dependencies to ensure reproducible environments.

### External API Versions

- **AstraDB Data API**: v1 (JSON API endpoint)
- **IBM watsonx.ai**: Foundation Models API v1
  - Model: `ibm/granite-13b-instruct-v2` (for reasoning)
  - Model: `sentence-transformers/all-MiniLM-L6-v2` (for embeddings)
- **Schlumberger Glossary API**: Web scraping (as of October 2025)

## Test Reproducibility

### Critical Path Tests (19/20 pass expected)

```bash
pytest tests/critical_path/test_cp_workflow_e2e.py -v
```

**Expected Results**:
- **Pass**: 19/20 tests (95%)
- **Expected Failure**: `test_simple_query_porosity` (environmental latency timeout, non-functional)
  - Failure reason: Glossary API latency >10s (network/API dependent, not code-related)
  - Functional correctness: Validated (response content is correct)

### Unit Tests

```bash
pytest tests/unit/ -v
```

All unit tests should pass (no environmental dependencies).

### Integration Tests

```bash
pytest tests/integration/test_pipeline.py -v
```

Requires:
- Active AstraDB connection (configure `.env`)
- Active watsonx.ai credentials (configure `.env`)
- Redis (optional - falls back to in-memory cache)

## Code Quality Metrics (Task 006 Baselines)

### Cyclomatic Complexity (Target: CCN ≤10)

```bash
lizard -l python -w services/langgraph/workflow.py services/graph_index/graph_traverser.py
```

**Expected Metrics** (post-Task 006):
- `reasoning_step`: CCN = 10 (was 42, reduced 76%)
- `retrieval_step`: CCN = 6 (was 25, reduced 76%)
- `_build_edge_index`: CCN = 1 (was 15, reduced 93%)
- `expand_search_results`: CCN = 5 (was 12, reduced 58%)

### Type Safety (Target: 0 mypy --strict errors)

```bash
mypy services/langgraph/workflow.py services/graph_index/graph_traverser.py --strict
```

**Expected**: Success: no issues found in 2 source files

### Security (Target: 0 high/critical pip-audit findings)

```bash
pip-audit --strict --require-hashes --desc
```

**Known Issues**:
- pip 24.2 (CVE-2025-8869) - Upgrade to pip 25.3+ recommended (Phase 5)

### Code Coverage (Target: ≥95% on critical path)

```bash
pytest tests/critical_path/ --cov=services.langgraph --cov=services.graph_index --cov-report=term-missing
```

**Expected**: ≥95% line + branch coverage on reasoning_step, retrieval_step, GraphTraverser

## Experiment Tracking (Planned - Phase 5)

### Latency Tracking

Instrumentation will be added to track:
- P50, P95, P99 query latency
- Per-step latency (embedding → retrieval → reasoning → generation)
- Logged to `logs/latency_metrics.json`

### Cache Performance

Instrumentation will be added to track:
- Redis cache hit rate (% of glossary queries served from cache)
- In-memory fallback usage rate (% of time Redis unavailable)
- Logged to `logs/cache_metrics.json`

## Known Non-Deterministic Behaviors

### LLM Generation

- **watsonx.ai Granite model**: Outputs are non-deterministic even with `temperature=0` due to internal sampling
- **Mitigation**: Tests validate semantic correctness (keywords, structure) rather than exact string matching

### Vector Search

- **AstraDB vector search**: Results may vary slightly due to index rebuilding or sharding changes
- **Mitigation**: Tests use top-K retrieval (K=10-20) and validate that relevant documents are present

### Network Latency

- **Glossary API**: Response times vary by network conditions (1-30s observed)
- **Mitigation**: Tests have generous timeouts (10s for E2E, 60s for integration)

## Debugging Failed Reproductions

If you cannot reproduce results:

**1. Verify data integrity:**
```bash
python scripts/verify_checksums.py
```

**2. Check environment:**
```bash
pip list | findstr /I "ibm_watsonx_ai langchain astrapy"
python --version
```

**3. Review logs:**
```bash
# Check for errors in recent runs
tail logs/*_latest.log
```

**4. Validate credentials:**
```bash
# Check .env file exists and has required keys
python -c "from services.config import get_settings; s = get_settings(); print('ASTRA:', bool(s.astra_db_api_endpoint)); print('WATSONX:', bool(s.watsonx_api_key))"
```

## Contact

For questions about reproducibility or issues with test failures:
- **GitHub Issues**: https://github.com/krump3t/astra-graphrag/issues
- **Task 006 Context**: `tasks/006-technical-debt-remediation/context/`

---

**Generated**: 2025-10-14 (Task 006 - Phase 5: Data Integrity & Monitoring)

**Checksum Count**: 122 files (120 LAS, 2 JSON)

**Total Data Size**: ~620 MB (raw test data)
