"""Retry utility with exponential backoff."""

from functools import wraps
from typing import Any, Callable, TypeVar, Union

from ..errors import TransientError, RequestError, TimeoutException


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    retry_exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = (
        TransientError,
        RequestError,
        TimeoutException,
    ),
) -> Callable[[Callable], Callable]:
    """Decorator for retrying failed operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds between retries
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential delay calculation
        retry_exceptions: Exceptions that should trigger a retry
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = min(
                            initial_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        import asyncio
                        await asyncio.sleep(delay)
                    
                    # Log the retry attempt
                    if attempt < max_retries:
                        print(f"Retry {attempt + 1}/{max_retries} for: {type(e).__name__}: {e}")
            
            # All retries exhausted, re-raise the last exception
            raise last_exception
        
        return wrapper
    
    return decorator


def retry_decorator(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    retry_exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = (
        TransientError,
        RequestError,
        TimeoutException,
    ),
) -> Callable:
    """Synchronous retry decorator (wraps in asyncio for async compatibility).
    
    This is a convenience wrapper for synchronous functions.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retry_exceptions=retry_exceptions,
            )(func)(*args, **kwargs)
        
        return async_wrapper
    
    return decorator


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        retry_exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = (
            TransientError,
            RequestError,
            TimeoutException,
        ),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_exceptions = retry_exceptions
    
    @classmethod
    def default(cls) -> "RetryConfig":
        """Return default retry configuration."""
        return cls()
