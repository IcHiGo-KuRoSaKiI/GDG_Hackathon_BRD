"""
Exponential backoff retry for LLM API calls.

Handles transient errors (503 overloaded, 429 rate limit, network issues)
without failing the entire pipeline.
"""

import logging
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# Error types that are safe to retry
_RETRYABLE_STATUS_CODES = {429, 503, 500}


def _is_retryable(exc: BaseException) -> bool:
    """Check if an exception is transient and safe to retry."""
    exc_str = str(exc)

    # Google genai SDK errors carry the status code in the message
    if any(f"{code}" in exc_str for code in _RETRYABLE_STATUS_CODES):
        return True

    # Check for known transient error class names
    exc_type = type(exc).__name__
    if exc_type in ("ServerError", "ServiceUnavailable", "ResourceExhausted"):
        return True

    # Network-level errors
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    return False


def with_retry(max_attempts: int = 5, min_wait: int = 2, max_wait: int = 60):
    """
    Decorator for retrying LLM API calls with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default 5)
        min_wait: Minimum wait in seconds between retries (default 2)
        max_wait: Maximum wait in seconds between retries (default 60)

    Backoff sequence: 2s → 4s → 8s → 16s → 32s (capped at max_wait)
    """
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
