"""Benchmark Service with Dependency Injection.

This service provides the core benchmarking functionality using dependency injection
to reduce tight coupling and improve testability.
"""

from typing import Optional, List, Dict, Any
import time

from .di import DependencyContainer, DependencyNotBoundError
from .errors import (
    BenchmarkError,
    LLMError,
    DatabaseError,
    PermanentError,
    RetryableError,
)
from .config import Config
from .logger import BenchmarkLogger
from .metrics import BenchmarkMetrics, MetricsCollector
from .runner import BenchmarkRunner
from .report import generate_report
from .schemas.benchmark import BenchmarkResult
from .schemas.corpus import Corpus


class BenchmarkService:
    """Core benchmarking service with dependency injection.
    
    This service encapsulates all benchmarking logic and uses dependency injection
    to receive its dependencies from a container, making it highly testable.
    
    Dependencies:
        - Config: Application configuration
        - BenchmarkLogger: Logging utilities
        - BenchmarkMetrics: Metrics collection
        - MetricsCollector: Performance metrics tracking
        - BenchmarkRunner: Execution engine
        - generate_report: Report generation
    """
    
    def __init__(self, container: DependencyContainer) -> None:
        """Initialize the benchmark service.
        
        Args:
            container: Dependency container providing all dependencies
        
        Raises:
            DependencyNotBoundError: If a required dependency is not bound
        """
        self._container = container
        
        # Resolve dependencies using dependency injection
        try:
            self._config = container.resolve(Config)
            self._logger = container.resolve(BenchmarkLogger)
            self._metrics = container.resolve(BenchmarkMetrics)
            self._metrics_collector = container.resolve(MetricsCollector)
            self._runner = container.resolve(BenchmarkRunner)
            self._report_generator = container.resolve(generate_report)
        except DependencyNotBoundError as e:
            self._logger.error(
                f"Failed to resolve dependency: {e.message}"
            )
            raise
    
    @property
    def config(self) -> Config:
        """Get the application configuration."""
        return self._config
    
    @property
    def logger(self) -> BenchmarkLogger:
        """Get the benchmark logger."""
        return self._logger
    
    @property
    def metrics(self) -> BenchmarkMetrics:
        """Get the benchmark metrics."""
        return self._metrics
    
    def run_benchmark(
        self,
        benchmark_name: str,
        corpus: Corpus,
        iterations: int = 1,
        timeout_seconds: Optional[int] = None
    ) -> BenchmarkResult:
        """Run a benchmark using the runner.
        
        Args:
            benchmark_name: Name of the benchmark to run
            corpus: The corpus to benchmark against
            iterations: Number of iterations (default: 1)
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            BenchmarkResult containing the benchmark data
            
        Raises:
            BenchmarkError: If the benchmark fails
            LLMError: If the LLM service is unavailable
            DatabaseError: If database operations fail
        """
        self._logger.info(
            f"Starting benchmark: {benchmark_name} "
            f"with {iterations} iterations"
        )
        
        try:
            # Run the benchmark using the injected runner
            result = self._runner.run(
                benchmark_name=benchmark_name,
                corpus=corpus,
                iterations=iterations,
                timeout=timeout_seconds
            )
            
            # Record metrics
            self._metrics_collector.record(
                benchmark_name=benchmark_name,
                iterations=iterations,
                total_time=result.total_time,
                avg_time=result.avg_time,
                success=True
            )
            
            self._logger.info(
                f"Benchmark completed: {benchmark_name} "
                f"in {result.total_time:.2f}s"
            )
            
            return result
            
        except RetryableError as e:
            self._logger.warning(
                f"Benchmark {benchmark_name} failed after retries: {e.message}"
            )
            raise PermanentError(
                f"Benchmark failed permanently: {e.message}"
            ) from e
        except Exception as e:
            self._logger.error(
                f"Benchmark {benchmark_name} failed: {e}"
            )
            raise BenchmarkError(
                f"Benchmark execution failed: {e}"
            ) from e
    
    def run_multiple_benchmarks(
        self,
        benchmark_names: List[str],
        corpus: Corpus,
        iterations: int = 1
    ) -> List[BenchmarkResult]:
        """Run multiple benchmarks sequentially.
        
        Args:
            benchmark_names: List of benchmark names to run
            corpus: The corpus to benchmark against
            iterations: Number of iterations per benchmark
            
        Returns:
            List of BenchmarkResult objects
        """
        results = []
        
        for benchmark_name in benchmark_names:
            try:
                result = self.run_benchmark(
                    benchmark_name=benchmark_name,
                    corpus=corpus,
                    iterations=iterations
                )
                results.append(result)
                
            except Exception as e:
                self._logger.error(
                    f"Benchmark {benchmark_name} failed: {e}"
                )
                raise
        
        return results
    
    def generate_report(
        self,
        benchmark_name: str,
        results: List[BenchmarkResult]
    ) -> str:
        """Generate a report for benchmark results.
        
        Args:
            benchmark_name: Name of the benchmark
            results: List of benchmark results
            
        Returns:
            Formatted report string
        """
        try:
            return self._report_generator(
                benchmark_name=benchmark_name,
                results=results
            )
        except Exception as e:
            self._logger.error(f"Report generation failed: {e}")
            return "Error generating report"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics.
        
        Returns:
            Dictionary containing benchmark metrics
        """
        return self._metrics.get_metrics()
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self._metrics.reset()
