# CP Test Validation Report
**Date**: 2025-10-14 07:38:11 UTC
**Protocol**: SCA v9-Compact

---

## Overall Summary

- **Total CP Test Files**: 3
- **Files Passing All Checks**: 0/3 (0%)
- **Avg Domain Specificity**: 100.0%
- **Avg Code Specificity**: 74.6%
- **Avg Authenticity**: 100.0%

## Coverage Analysis

- **Line Coverage**: 43.4% (threshold: ≥95%)
- **Branch Coverage**: 43.4% (threshold: ≥85%)
- **Status**: FAIL

## Detailed Results by File

### test_cp_glossary_scraper.py

**Domain Specificity**: 100.0% PASS

**Code Specificity**: 85.7% FAIL

Issues:
- Code specificity score 85.7% below 90% threshold
- Found 3 generic patterns in 21 tests
-   - Line 153: assert result is not None
-   - Line 276: assert result is not None
-   - Line 52: assert len(definition.definition) > 0

Recommendations:
- Replace generic assertions with specific value checks
- Add assertions that verify implementation details
- Remove TODO/skipped tests or implement them

**Authenticity**: 100.0% PASS

### test_cp_mcp_tools.py

**Domain Specificity**: 100.0% PASS

**Code Specificity**: 63.0% FAIL

Issues:
- Code specificity score 63.0% below 90% threshold
- Found 10 generic patterns in 27 tests
-   - Line 63: assert result is not None
-   - Line 77: assert result is not None
-   - Line 100: assert len(result["content"]) > 0

Recommendations:
- Replace generic assertions with specific value checks
- Add assertions that verify implementation details
- Remove TODO/skipped tests or implement them

**Authenticity**: 100.0% PASS

### test_cp_workflow_reasoning.py

**Domain Specificity**: 100.0% PASS

**Code Specificity**: 75.0% FAIL

Issues:
- Code specificity score 75.0% below 90% threshold
- Found 5 generic patterns in 20 tests
-   - Line 75: assert result is not None
-   - Line 100: assert result is not None
-   - Line 143: assert len(embedding) > 0

Recommendations:
- Replace generic assertions with specific value checks
- Add assertions that verify implementation details
- Remove TODO/skipped tests or implement them

**Authenticity**: 100.0% PASS
