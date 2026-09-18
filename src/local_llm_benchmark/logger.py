"""Structured logging utilities for the LLM benchmarking system.

This module provides a centralized logging system with:
- Structured JSON log output for programmatic parsing
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console and file handlers
- Thread-safe implementation
- Custom log levels for benchmark-specific events

Usage:
    >>> from local_llm_benchmark.logger import StructuredLogger
    >>> logger = StructuredLogger("benchmark")
    >>> logger.info("Starting benchmark")
    >>> logger.error("Benchmark failed", duration=120.5)
"""

import logging
import json
from datetime import datetime
from typing import Any
import sys


class StructuredLogger:
    """Structured logger with JSON output support.
    
    Provides both human-readable console output and structured JSON
    logs to files for programmatic analysis.
    
    Attributes:
        logger: Underlying Python logging.Logger instance
        name: Logger name used for file naming
    """
    
    def __init__(self, name: str):
        """Initialize the structured logger.
        
        Args:
            name: Logger name used for identification and file naming
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler for human-readable output
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console)
        
        # File handler for structured logs
        file_handler = logging.FileHandler(
            f"{name}.log",
            encoding='utf-8',
            mode='a'  # Append mode
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        ))
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs) -> None:
        """Log an INFO level message with structured JSON output.
        
        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": message,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry, default=str))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log a WARNING level message with structured JSON output.
        
        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "message": message,
            **kwargs
        }
        self.logger.warning(json.dumps(log_entry, default=str))
    
    def error(self, message: str, **kwargs) -> None:
        """Log an ERROR level message with structured JSON output.
        
        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "message": message,
            **kwargs
        }
        self.logger.error(json.dumps(log_entry, default=str))
    
    def debug(self, message: str, **kwargs) -> None:
        """Log a DEBUG level message.
        
        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log entry
        """
        self.logger.debug(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log a CRITICAL level message with structured JSON output.
        
        Args:
            message: The log message
            **kwargs: Additional key-value pairs to include in the log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "CRITICAL",
            "message": message,
            **kwargs
        }
        self.logger.critical(json.dumps(log_entry, default=str))
    
    def exception(self, message: str, **kwargs) -> None:
        """Log an exception with structured JSON output.
        
        Args:
            message: The log message
            exc: Exception instance to log
            **kwargs: Additional key-value pairs to include in the log entry
        """
        self.logger.exception(message, extra=kwargs)


class BenchmarkLogger(StructuredLogger):
    """Specialized logger for benchmark operations.
    
    Provides additional context for benchmark-specific logging.
    """
    
    def __init__(self, name: str):
        """Initialize the benchmark logger.
        
        Args:
            name: Logger name (e.g., "benchmark.challenge", "benchmark.engine")
        """
        super().__init__(name)
    
    def benchmark_start(self, operation: str, **kwargs) -> None:
        """Log the start of a benchmark operation.
        
        Args:
            operation: Description of the operation being benchmarked
            **kwargs: Additional context (benchmark_id, challenge_id, etc.)
        """
        self.info(f"Benchmark started: {operation}", **kwargs)
    
    def benchmark_end(self, operation: str, **kwargs) -> None:
        """Log the end of a benchmark operation.
        
        Args:
            operation: Description of the operation being benchmarked
            duration: Duration in seconds
            **kwargs: Additional context
        """
        self.info(f"Benchmark completed: {operation}", **kwargs)
    
    def request_sent(self, endpoint: str, method: str, **kwargs) -> None:
        """Log a request being sent.
        
        Args:
            endpoint: API endpoint being called
            method: HTTP method
            **kwargs: Request context
        """
        self.debug(f"Request sent: {method} {endpoint}", **kwargs)
    
    def request_received(self, endpoint: str, status: int, duration: float, **kwargs) -> None:
        """Log a request response.
        
        Args:
            endpoint: API endpoint
            status: HTTP status code
            duration: Response time in seconds
            **kwargs: Response context
        """
        self.debug(f"Request received: {status} {endpoint} (duration: {duration:.3f}s)", **kwargs)
    
    def token_used(self, prompt_tokens: int, completion_tokens: int, **kwargs) -> None:
        """Log token usage for LLM calls.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            **kwargs: Additional context
        """
        self.debug(f"Tokens used: {prompt_tokens} prompt, {completion_tokens} completion", **kwargs)


# ============================================================================
# Global Logger Instances
# ============================================================================

# Create root logger instance
_root_logger = StructuredLogger("benchmark")

# Convenience logger instances for common modules
logger = _root_logger
benchmark = BenchmarkLogger("benchmark")
api_logger = BenchmarkLogger("benchmark.api")
engine_logger = BenchmarkLogger("benchmark.engine")
cache_logger = BenchmarkLogger("benchmark.cache")


def get_logger(name: str) -> StructuredLogger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Module name for the logger
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


def setup_log_level(level: int) -> None:
    """Set the global minimum log level.
    
    Args:
        level: Logging level (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)
    """
    _root_logger.logger.setLevel(level)


if __name__ == "__main__":
    # Demo usage
    logger = logger
    
    logger.info("Application starting")
    logger.debug("Debug information")
    logger.warning("This is a warning")
    logger.error("This is an error")
    logger.critical("Critical failure")
    
    benchmark = benchmark
    benchmark.benchmark_start("Challenge execution", challenge_id="c1")
    benchmark.benchmark_end("Challenge execution", challenge_id="c1", duration=2.5)
    
    api_logger = api_logger
    api_logger.request_sent("/v1/chat/completions", "POST")
    api_logger.request_received("/v1/chat/completions", 200, 0.45)
    api_logger.token_used(prompt_tokens=100, completion_tokens=200)
