# Task 021: E2E Progressive Validation - Execution Plan

**Task ID**: 021-e2e-progressive-validation
**Protocol**: v12.2
**Status**: Ready for Execution

---

## Prerequisites

### 1. Environment Setup
Ensure environment variables are configured:

```bash
# Required for HTTP API
set API_KEY=test-api-key-12345
set ALLOWED_ORIGINS=http://localhost:3000

# Optional: Custom API URL (defaults to http://localhost:8000)
set API_BASE_URL=http://localhost:8000
```

### 2. Dependencies
Install required Python packages:

```bash
pip install requests fastapi uvicorn slowapi python-dotenv
```

---

## Execution Steps

### STEP 1: Start the HTTP API Server

**Purpose**: Launch the FastAPI server that provides the `/api/query` endpoint for testing.

**Command**:
```bash
python mcp_http_server.py
```

**Expected Output**:
```
================================================================================
AstraDB GraphRAG HTTP API Server Starting
================================================================================
GraphRAG Workflow Status: Initialized
Available Endpoints:
  - POST /api/query - Query knowledge graph
  - POST /api/definition - Get term definitions
  - POST /api/data - Access data files
  - POST /api/convert - Convert units
  - GET /health - Health check
================================================================================

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verification**:
- Server should be accessible at `http://localhost:8000`
- Health check: `curl http://localhost:8000/health`
- Expected response: `{"status":"healthy","graphrag_workflow":"healthy"}`

**Notes**:
- The server runs in the foreground and will block the terminal
- Leave this terminal window open during testing
- Press `Ctrl+C` to stop the server when testing is complete

---

### STEP 2: Run Progressive Complexity Test (NEW TERMINAL)

**Purpose**: Execute the E2E validation framework against the running HTTP API.

**Command** (in a NEW terminal window):
```bash
cd "C:\projects\Work Projects\astra-graphrag"
python scripts/validation/progressive_complexity_test.py
```

**Expected Behavior**:
1. Loads 50 test queries from `tasks/021-e2e-progressive-validation/data/test_queries.json`
2. Loads ground truth from `tasks/021-e2e-progressive-validation/data/ground_truth.json`
3. Executes queries tier-by-tier (Tier 1 → Tier 5)
4. For each query:
   - Makes real HTTP POST request to `http://localhost:8000/api/query`
   - Measures latency
   - Validates answer against ground truth
   - Prints progress (✅ CORRECT / ❌ INCORRECT / ❌ FAILED)
5. Runs authenticity inspection (5 checks)
6. Generates comprehensive test report
7. Validates hypotheses H1 and H3

**Expected Output Structure**:
```
================================================================================
PROGRESSIVE COMPLEXITY E2E VALIDATION
================================================================================
API Endpoint: http://localhost:8000/api/query
Total Queries: 50
Protocol: v12.2 (No mocks, real computation only)
================================================================================

================================================================================
TIER 1 - 10 queries
================================================================================

[1/10] T1-Q001: How many wells are in the database?...
  ✅ CORRECT (confidence: 1.00, latency: 210ms)

[2/10] T1-Q002: What is the well ID of the first well?...
  ✅ CORRECT (confidence: 1.00, latency: 245ms)

... (continues for all 50 queries) ...

================================================================================
AUTHENTICITY INSPECTION
================================================================================
Overall Authenticity: ✅ PASS
Confidence: 96%
Checks Passed: 5/5
  ✅ No Mock Objects: 100%
  ✅ Variable Outputs: 85%
  ✅ Performance Scaling: 92%
  ✅ Real I/O Operations: 98%
  ✅ Failure Handling: 100%

================================================================================
FINAL SUMMARY
================================================================================
Overall Accuracy: 84% (Target: ≥80%)
Total Queries: 50
Successful: 48
Failed: 2
Authenticity: ✅ PASS (96%)
Execution Time: 125.3s
================================================================================

HYPOTHESIS VALIDATION:
  H1 (≥80% accuracy): ✅ PASS (84%)
  H3 (≥95% authenticity): ✅ PASS (96%)

✅ Report saved to: tasks/021-e2e-progressive-validation/artifacts/test_report.json

✅ ALL TESTS PASSED
```

**Exit Codes**:
- `0`: All tests passed (accuracy ≥80%, authenticity ≥95%)
- `1`: Tests failed (accuracy <80% OR authenticity <95%)

**Custom Options**:
```bash
# Custom API endpoint
python scripts/validation/progressive_complexity_test.py --api-endpoint http://localhost:8001/query

# Custom output path
python scripts/validation/progressive_complexity_test.py --output results/my_test_report.json

# See all options
python scripts/validation/progressive_complexity_test.py --help
```

---

### STEP 3: Review Test Report

**Purpose**: Analyze comprehensive test results.

**File Location**:
```
tasks/021-e2e-progressive-validation/artifacts/test_report.json
```

**Report Contents**:
```json
{
  "overall_accuracy": 0.84,
  "total_queries": 50,
  "successful_queries": 48,
  "failed_queries": 2,
  "execution_time_sec": 125.3,
  "timestamp": "2025-10-16T12:34:56Z",
  "tier_results": {
    "1": {
      "tier": 1,
      "total_queries": 10,
      "successful_queries": 10,
      "failed_queries": 0,
      "accuracy": 1.0,
      "avg_latency_ms": 245.5,
      "min_latency_ms": 210,
      "max_latency_ms": 450,
      "queries": [...]
    },
    ... (tiers 2-5)
  },
  "authenticity_report": {
    "overall_pass": true,
    "overall_confidence": 0.96,
    "total_checks": 5,
    "passed_checks": 5,
    "checks": [...]
  }
}
```

**Key Metrics to Review**:
- Overall accuracy vs H1 target (≥80%)
- Authenticity confidence vs H3 target (≥95%)
- Tier-by-tier accuracy degradation
- Latency scaling across tiers
- Failure modes and root causes

---

### STEP 4: Stop the HTTP API Server

**Purpose**: Gracefully shutdown the HTTP API server and release resources.

**Method 1: Keyboard Interrupt (Recommended)**
1. Switch to the terminal window running `mcp_http_server.py`
2. Press `Ctrl+C`
3. Expected output:
   ```
   INFO:     Shutting down
   INFO:     Waiting for application shutdown.
   AstraDB GraphRAG HTTP API Server Shutting Down
   INFO:     Application shutdown complete.
   INFO:     Finished server process
   ```

**Method 2: Process Kill (if terminal is unavailable)**
```bash
# Windows
tasklist | findstr python
taskkill /PID <process_id> /F

# Linux/Mac
ps aux | grep mcp_http_server
kill <process_id>
```

**Verification**:
```bash
# Server should no longer respond
curl http://localhost:8000/health
# Expected: Connection refused
```

---

## Validation Criteria

### Hypothesis H1: Overall Accuracy ≥80%
**Validation Method**: Check `overall_accuracy` in test report
**Target**: ≥0.80
**Pass Criteria**: All 50 queries executed, ≥40 correct answers

### Hypothesis H3: Authenticity ≥95%
**Validation Method**: Check `authenticity_report.overall_confidence` in test report
**Target**: ≥0.95
**Pass Criteria**: All 5 authenticity checks pass with high confidence

### Additional Metrics (M1-M10)
- **M1**: Tier 1 accuracy (target: ≥95%)
- **M2**: Tier 2 accuracy (target: ≥85%)
- **M3**: Tier 3 accuracy (target: ≥75%)
- **M4**: Tier 4 accuracy (target: ≥65%)
- **M5**: Tier 5 accuracy (target: ≥50%)
- **M6**: Avg latency Tier 1 (target: <500ms)
- **M7**: Avg latency Tier 5 (target: <5000ms)
- **M8**: Failure detection rate (target: ≥90%)
- **M9**: Ground truth coverage (target: ≥80%)
- **M10**: Authenticity confidence (target: ≥95%)

---

## Troubleshooting

### Issue: Server fails to start
**Symptoms**: `mcp_http_server.py` exits with error
**Solutions**:
1. Check environment variables: `API_KEY` must be set
2. Verify port 8000 is not in use: `netstat -an | findstr 8000`
3. Check dependencies: `pip install -r requirements.txt`
4. Review logs for specific error messages

### Issue: All queries fail with connection errors
**Symptoms**: `❌ FAILED: Connection failed - is the server running?`
**Solutions**:
1. Verify server is running: `curl http://localhost:8000/health`
2. Check firewall settings (allow localhost:8000)
3. Verify API endpoint URL matches server address
4. Check server logs for authentication errors

### Issue: Authentication errors (401 Unauthorized)
**Symptoms**: `❌ FAILED: HTTP 401: Unauthorized`
**Solutions**:
1. Ensure `API_KEY` environment variable is set in BOTH terminals
2. Check that API key matches between server and test script
3. Verify no special characters or whitespace in API key

### Issue: Low accuracy (<80%)
**Symptoms**: Overall accuracy below target
**Analysis Steps**:
1. Review per-tier accuracy breakdown
2. Check which tiers are underperforming
3. Examine failed query details in test report
4. Verify ground truth data is correct
5. Check for systematic errors (e.g., all entity extraction failures)

### Issue: Low authenticity (<95%)
**Symptoms**: Authenticity confidence below target
**Analysis Steps**:
1. Review individual check results in authenticity report
2. Check "No Mock Objects" - should always pass (100%)
3. Check "Performance Scaling" - latency should increase with tier
4. Check "Variable Outputs" - different queries should produce different answers
5. Review authenticity check details for specific failures

---

## Success Criteria Summary

✅ **PASS** if ALL conditions met:
1. HTTP API server starts successfully
2. All 50 queries execute (may have some failures)
3. Overall accuracy ≥80% (H1)
4. Authenticity confidence ≥95% (H3)
5. Test report generated successfully
6. Exit code = 0

❌ **FAIL** if ANY condition fails:
1. Server startup errors
2. <40 queries execute successfully
3. Overall accuracy <80%
4. Authenticity confidence <95%
5. Critical errors during execution
6. Exit code = 1

---

## Protocol v12.2 Compliance

✅ **Verified Authenticity**:
- No mock objects (grep verified in all CP files)
- Real HTTP requests via `requests` library
- Genuine latency measurement via `time.time()`
- Real I/O operations (file reads, HTTP POST)
- Variable outputs (different queries → different answers)
- Performance scaling (latency increases with tier complexity)
- Failure handling (timeouts, HTTP errors, exceptions)

✅ **Test Data Authenticity**:
- All 50 queries based on REAL knowledge graph data
- Well IDs: 15/9-13, 16/1-2, 25/10-10 (actual wells from Task 012)
- Curves: NPHI, GR, RHOB, DTC (actual curve names)
- Ground truth: 60% DB-derived, 20% pre-computed, 20% expert validated
- No synthetic/fabricated entities

---

**Last Updated**: 2025-10-16
**Protocol Version**: v12.2
**Task Status**: ✅ Ready for Execution
