"""Retry decorator with exponential backoff and jitter.

Provides a project-wide retry utility that complements the existing
tenacity usage in infrastructure/router.py. Supports both sync and
async callables, configurable backoff strategies, and exception filtering.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, ParamSpec, Sequence

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        last_exception: BaseException,
        attempts: int,
        func_name: str,
    ):
        self.last_exception = last_exception
        self.attempts = attempts
        self.func_name = func_name
        super().__init__(
            f"Retry exhausted for '{func_name}' after {attempts} attempts: {last_exception}"
        )


@dataclass
class RetryStats:
    """Tracks retry statistics for a single invocation."""
    attempts: int = 0
    total_delay_ms: float = 0.0
    exceptions: list[BaseException] = field(default_factory=list)
    succeeded: bool = False


def _compute_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    backoff_factor: float,
    jitter: bool,
) -> float:
    delay = base_delay * (backoff_factor ** (attempt - 1))
    delay = min(delay, max_delay)
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Sequence[type[BaseException]] = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that retries a callable on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first call).
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        backoff_factor: Multiplier for exponential backoff.
        jitter: Add random jitter to the delay (0.5x to 1.0x).
        retryable_exceptions: Tuple of exception types to retry on.
        on_retry: Callback(attempt_number, exception, delay_seconds) on each retry.

    Returns:
        Decorated callable with retry logic.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        is_coroutine = asyncio.iscoroutinefunction(func)

        if is_coroutine:
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                stats = RetryStats()
                last_exc: BaseException | None = None

                for attempt in range(1, max_attempts + 1):
                    stats.attempts = attempt
                    try:
                        result = await func(*args, **kwargs)
                        stats.succeeded = True
                        if stats.attempts > 1:
                            logger.info(
                                "Retry succeeded for '%s' on attempt %d/%d (total_delay=%.1fms)",
                                func.__name__, attempt, max_attempts, stats.total_delay_ms,
                            )
                        return result
                    except retryable_exceptions as exc:
                        last_exc = exc
                        stats.exceptions.append(exc)
                        if attempt == max_attempts:
                            break
                        delay = _compute_delay(attempt, base_delay, max_delay, backoff_factor, jitter)
                        stats.total_delay_ms += delay * 1000
                        logger.warning(
                            "Retry %d/%d for '%s' after %s: %s (next retry in %.2fs)",
                            attempt, max_attempts, func.__name__, type(exc).__name__, exc, delay,
                        )
                        if on_retry:
                            on_retry(attempt, exc, delay)
                        await asyncio.sleep(delay)

                raise RetryExhausted(last_exc, max_attempts, func.__name__)

            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                stats = RetryStats()
                last_exc: BaseException | None = None

                for attempt in range(1, max_attempts + 1):
                    stats.attempts = attempt
                    try:
                        result = func(*args, **kwargs)
                        stats.succeeded = True
                        if stats.attempts > 1:
                            logger.info(
                                "Retry succeeded for '%s' on attempt %d/%d (total_delay=%.1fms)",
                                func.__name__, attempt, max_attempts, stats.total_delay_ms,
                            )
                        return result
                    except retryable_exceptions as exc:
                        last_exc = exc
                        stats.exceptions.append(exc)
                        if attempt == max_attempts:
                            break
                        delay = _compute_delay(attempt, base_delay, max_delay, backoff_factor, jitter)
                        stats.total_delay_ms += delay * 1000
                        logger.warning(
                            "Retry %d/%d for '%s' after %s: %s (next retry in %.2fs)",
                            attempt, max_attempts, func.__name__, type(exc).__name__, exc, delay,
                        )
                        if on_retry:
                            on_retry(attempt, exc, delay)
                        time.sleep(delay)

                raise RetryExhausted(last_exc, max_attempts, func.__name__)

            return sync_wrapper  # type: ignore

    return decorator


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """Programmatic retry for async callables (not a decorator).

    Useful when the function to retry is determined at runtime.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = _compute_delay(attempt, base_delay, max_delay, backoff_factor, jitter)
            logger.warning(
                "Retry %d/%d for '%s': %s (next retry in %.2fs)",
                attempt, max_attempts, getattr(func, "__name__", str(func)), exc, delay,
            )
            await asyncio.sleep(delay)

    raise RetryExhausted(last_exc, max_attempts, getattr(func, "__name__", str(func)))
