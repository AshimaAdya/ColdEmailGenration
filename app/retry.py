import time
import random
import functools
import logging

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator with exponential backoff for LLM API calls."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    err_str = str(e).lower()
                    # Only retry on rate-limit / transient errors
                    is_retriable = any(
                        token in err_str
                        for token in ["rate limit", "429", "503", "timeout", "connection"]
                    )
                    if not is_retriable:
                        raise
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                        logger.warning(
                            "Retriable error on attempt %d/%d for %s: %s. Retrying in %.1fs.",
                            attempt + 1, max_attempts, func.__name__, e, delay
                        )
                        time.sleep(delay)
            raise RuntimeError(
                f"LLM service unavailable after {max_attempts} attempts: {last_exc}"
            )
        return wrapper
    return decorator
