import asyncio
import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Tuple, Type

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    max_retries: int = 3
    delay: float = 1.0
    backoff: float = 2.0
    exceptions: Tuple[Type[Exception], ...] = field(default_factory=lambda: (Exception,))


class ExponentialBackoff:
    def __init__(self, base_delay: float = 1.0, backoff_factor: float = 2.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


async def retry_async(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    *args: Any,
    **kwargs: Any,
) -> Any:
    backoff_strategy = ExponentialBackoff(base_delay=delay, backoff_factor=backoff)
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as exc:
            last_exception = exc
            if attempt < max_retries:
                wait_time = backoff_strategy.get_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {wait_time:.1f}s. "
                    f"Error: {exc}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} retries exhausted for {func.__name__}. Last error: {exc}")

    raise last_exception  # type: ignore[misc]


def retry(config: RetryConfig | None = None):
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_async(
                func,
                max_retries=config.max_retries,
                delay=config.delay,
                backoff=config.backoff,
                exceptions=config.exceptions,
                *args,
                **kwargs,
            )
        return wrapper
    return decorator
