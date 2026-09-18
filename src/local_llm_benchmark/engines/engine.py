"""Robust LLM engine with graceful degradation and fallback support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from ..errors import TransientError, BenchmarkError
from ..logger import BenchmarkLogger, logger
from ..schemas.engine import EngineConfig, EngineResult


@dataclass
class EngineStats:
    """Statistics and metrics for engine performance."""
    total_tokens: int = 0
    total_time_ms: float = 0.0
    tokens_per_second: float = 0.0
    throughput_tokens_per_min: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0


@dataclass
class EngineMetrics:
    """Performance metrics for engine evaluation."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    bleu_score: float = 0.0
    perplexity: float = float('inf')


class BaseEngine(ABC):
    """Abstract base class for all LLM engine implementations.
    
    All engine implementations must inherit from this class and implement
    the required abstract methods for benchmarking operations.
    """
    
    name: str = "Base Engine"
    
    def __init__(self, config: EngineConfig):
        """Initialize the engine with configuration.
        
        Args:
            config: Engine configuration settings
        """
        self.config = config
        self._stats = EngineStats()
        self._metrics = EngineMetrics()
        
    @property
    def stats(self) -> EngineStats:
        """Get current engine statistics."""
        return self._stats
    
    @property
    def metrics(self) -> EngineMetrics:
        """Get current engine metrics."""
        return self._metrics
    
    @property
    def config(self) -> EngineConfig:
        """Get engine configuration."""
        return self._config
    
    @property
    def logger(self) -> BenchmarkLogger:
        """Get benchmark logger for this engine."""
        return BenchmarkLogger(f"benchmark.engine.{self.name}")
    
    @abstractmethod
    def benchmark(self, prompts: list[str], max_tokens: int) -> list[EngineResult]:
        """Run benchmark on a set of prompts.
        
        Args:
            prompts: List of prompt strings to benchmark
            max_tokens: Maximum tokens to generate per response
            
        Returns:
            List of EngineResult objects for each prompt
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def evaluate(self, response: str, expected: str) -> float:
        """Evaluate response quality against expected output.
        
        Args:
            response: Generated response text
            expected: Expected/reference response
            
        Returns:
            Evaluation score between 0.0 and 1.0
        """
        pass
    
    def reset_stats(self) -> None:
        """Reset engine statistics."""
        self._stats = EngineStats()
        self._metrics = EngineMetrics()
    
    def reset_metrics(self) -> None:
        """Reset engine metrics."""
        self._metrics = EngineMetrics()
    
    def get_status(self) -> dict[str, Any]:
        """Get engine status as a dictionary."""
        return {
            "name": self.name,
            "config": {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            },
            "stats": {
                "total_tokens": self._stats.total_tokens,
                "total_time_ms": self._stats.total_time_ms,
                "tokens_per_second": self._stats.tokens_per_second,
                "throughput_tokens_per_min": self._stats.throughput_tokens_per_min,
                "latency_ms": self._stats.latency_ms,
                "error_count": self._stats.error_count,
                "success_count": self._stats.success_count
            },
            "metrics": {
                "accuracy": self._metrics.accuracy,
                "precision": self._metrics.precision,
                "recall": self._metrics.recall,
                "f1_score": self._metrics.f1_score,
                "bleu_score": self._metrics.bleu_score,
                "perplexity": self._metrics.perplexity
            }
        }


class RobustLLMEngine(BaseEngine):
    """LLM engine with graceful degradation.
    
    This engine provides fallback support for primary engine failures.
    When the primary engine encounters a TransientError, it automatically
    falls back to a secondary engine if configured.
    """
    
    def __init__(
        self,
        primary: BaseEngine,
        fallback: Optional[BaseEngine] = None,
        fallback_enabled: bool = True,
        config: Optional[EngineConfig] = None,
    ):
        """Initialize the robust engine.
        
        Args:
            primary: Primary engine instance
            fallback: Optional secondary/fallback engine
            fallback_enabled: Whether fallback is enabled
            config: Engine configuration (overrides primary)
        """
        self.primary = primary
        self.fallback = fallback
        self.fallback_enabled = fallback_enabled
        
        # Use provided config or fall back to primary config
        self._config = config or primary.config
        
        # Override name to indicate robustness
        self.name = f"RobustLLMEngine ({primary.name})"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate with fallback to secondary engine.
        
        Args:
            prompt: Input prompt text
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
            
        Raises:
            TransientError: If primary fails and fallback is not available
            BenchmarkError: If both engines fail
        """
        try:
            return await self.primary.generate(prompt, **kwargs)
        except TransientError as e:
            if self.fallback_enabled:
                self.logger.warning(
                    f"Primary engine failed, falling back: {e}"
                )
                try:
                    return await self.fallback.generate(prompt, **kwargs)
                except Exception as fallback_error:
                    self.logger.error(
                        f"Fallback engine also failed: {fallback_error}"
                    )
                    raise BenchmarkError(
                        f"All engines failed: primary ({e}), fallback ({fallback_error})"
                    )
            else:
                raise
    
    async def benchmark(self, prompts: list[str], max_tokens: int) -> list[EngineResult]:
        """Run benchmark with fallback support.
        
        Args:
            prompts: List of prompt strings to benchmark
            max_tokens: Maximum tokens to generate per response
            
        Returns:
            List of EngineResult objects for each prompt
        """
        results = []
        for prompt in prompts:
            try:
                result = await self.primary.benchmark([prompt], max_tokens)
                results.extend(result)
            except TransientError as e:
                if self.fallback_enabled and self.fallback:
                    self.logger.warning(
                        f"Primary engine failed for prompt, falling back: {e}"
                    )
                    try:
                        result = await self.fallback.benchmark([prompt], max_tokens)
                        results.extend(result)
                    except Exception as fallback_error:
                        self.logger.error(
                            f"Fallback engine also failed: {fallback_error}"
                        )
                        # Record failed result
                        results.append(EngineResult(
                            prompt=prompt,
                            response=None,
                            success=False,
                            error=str(e) if isinstance(e, Exception) else str(e),
                            metrics=None,
                        ))
                else:
                    results.append(EngineResult(
                        prompt=prompt,
                        response=None,
                        success=False,
                        error=str(e) if isinstance(e, Exception) else str(e),
                        metrics=None,
                    ))
        
        return results
    
    async def evaluate(self, response: str, expected: str) -> float:
        """Evaluate response quality.
        
        Args:
            response: Generated response text
            expected: Expected/reference response
            
        Returns:
            Evaluation score between 0.0 and 1.0
        """
        return await self.primary.evaluate(response, expected)
    
    def reset_stats(self) -> None:
        """Reset engine statistics."""
        self.primary.reset_stats()
        if self.fallback:
            self.fallback.reset_stats()
    
    def reset_metrics(self) -> None:
        """Reset engine metrics."""
        self.primary.reset_metrics()
        if self.fallback:
            self.fallback.reset_metrics()
    
    def get_status(self) -> dict[str, Any]:
        """Get engine status including fallback information."""
        status = super().get_status()
        status["fallback_enabled"] = self.fallback_enabled
        status["fallback_configured"] = self.fallback is not None
        
        if self.fallback:
            status["fallback_status"] = self.fallback.get_status()
        
        return status
