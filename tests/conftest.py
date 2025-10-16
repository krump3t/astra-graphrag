"""Global pytest configuration and fixtures for astra-graphrag tests.

Task 018: Production Remediation
- Suppress SlowAPI Redis connection warnings (P2-10)
"""
import logging

import pytest


@pytest.fixture(autouse=True)
def suppress_redis_warnings():
    """
    Suppress Redis connection warnings from SlowAPI during tests.

    Issue (P2-10): SlowAPI logs "Redis unavailable" warnings when Redis
    is not running, cluttering test output and potentially masking real warnings.

    Solution: Temporarily raise SlowAPI logger level to ERROR during tests,
    suppressing INFO/WARNING level messages about Redis connection failures.

    This is safe because:
    - Tests use in-memory fallback when Redis unavailable
    - Rate limiting functionality is still validated
    - Production deployment will have Redis configured

    Scope: Applies to all tests (autouse=True)
    """
    # Suppress SlowAPI warnings during test execution
    slowapi_logger = logging.getLogger("slowapi")
    original_level = slowapi_logger.level
    slowapi_logger.setLevel(logging.ERROR)

    yield

    # Restore original logging level after test
    slowapi_logger.setLevel(original_level)
