"""Retry utilities for production-grade API resilience.

Implements exponential backoff with configurable retries for transient errors.
Used by AstraDB and WatsonX clients to handle network failures gracefully.

PRODUCTION RESILIENCE (Task 006 - Phase 4): Implements ADR-006-009 retry strategy.
"""
import time
import logging
from typing import Callable, TypeVar, Any
from functools import wraps
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Transient HTTP status codes that should trigger retries
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that adds exponential backoff retry logic to a function.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def make_api_call():
            # ... API call logic ...
            pass

        # On failure: retries after 1s, 2s, 4s delays
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: HTTPError | URLError | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except HTTPError as e:
                    # Only retry on transient errors
                    if e.code not in RETRYABLE_STATUS_CODES:
                        raise

                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"{func.__name__} failed with HTTP {e.code}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: HTTP {e.code}"
                        )

                except URLError as e:
                    # Network errors (DNS, connection refused, timeout)
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"{func.__name__} network error, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )

            # All retries exhausted
            if last_exception:
                raise last_exception

            # Should never reach here, but for type safety
            raise RuntimeError(f"{func.__name__} failed after {max_retries} retries")

        return wrapper
    return decorator
