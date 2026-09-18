"""Backoff utility for retry logic.

This module provides exponential backoff utilities for handling transient
failures in async operations, particularly useful for LLM API calls.
"""

import time
import random
from enum import Enum
from typing import Optional
from backoff import exponential_backoff, on_backoff, linear_backoff


class BackoffStrategy(Enum):
    """Backoff strategy for retry logic."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


async def calculate_backoff_interval(
    attempt: int,
    base_delay: float,
    max_delay: float,
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
) -> float:
    """Calculate backoff interval based on attempt number and strategy.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        strategy: Backoff strategy to use
    
    Returns:
        Delay interval in seconds
    """
    if strategy == BackoffStrategy.EXPONENTIAL:
        # Exponential backoff with jitter
        delay = base_delay * (2 ** attempt)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        delay = min(delay + jitter, max_delay)
    elif strategy == BackoffStrategy.LINEAR:
        # Linear backoff with jitter
        delay = base_delay * (1 + attempt)
        jitter = random.uniform(0, delay * 0.1)
        delay = min(delay + jitter, max_delay)
    else:
        delay = base_delay
    
    return delay


def exponential_backoff_decorator(
    max_retries: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    **kwargs
) -> type:
    """Decorator for exponential backoff with jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
    """
    def decorator(func):
        @exponential_backoff(
            max_attempts=max_retries + 1,  # +1 because attempt 0 is first try
            max_value=max_delay,
            initial_interval=initial_delay,
            multiplier=2,
            jitter=jitter,
            giveup=lambda attempt: attempt > max_retries
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def linear_backoff_decorator(
    max_retries: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    **kwargs
) -> type:
    """Decorator for linear backoff with jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
    """
    def decorator(func):
        @linear_backoff(
            max_attempts=max_retries + 1,  # +1 because attempt 0 is first try
            max_value=max_delay,
            initial_interval=initial_delay,
            jitter=jitter,
            giveup=lambda attempt: attempt > max_retries
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def on_backoff_handler(
    retry: int,
    max_retries: int,
    delay: float,
    attempt: int,
    **kwargs
) -> Optional[str]:
    """Custom handler for on_backoff decorator.
    
    Returns a message to display during backoff, or None to suppress.
    
    Args:
        retry: Number of retries remaining
        max_retries: Maximum allowed retries
        delay: Delay duration
        attempt: Current attempt number
    """
    remaining = max_retries - attempt
    if remaining > 0:
        return f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})..."
    return None


def retry_with_backoff(
    func,
    max_retries: int,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    **kwargs
):
    """Retry wrapper with configurable backoff strategy.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        strategy: Backoff strategy to use
    """
    if strategy == BackoffStrategy.EXPONENTIAL:
        return exponential_backoff(
            max_attempts=max_retries + 1,
            max_value=max_delay,
            initial_interval=initial_delay,
            multiplier=2,
            jitter=True,
            giveup=lambda attempt: attempt > max_retries
        )(func)
    elif strategy == BackoffStrategy.LINEAR:
        return linear_backoff(
            max_attempts=max_retries + 1,
            max_value=max_delay,
            initial_interval=initial_delay,
            jitter=True,
            giveup=lambda attempt: attempt > max_retries
        )(func)
    else:
        return func
