"""Shared test fixtures for the LLM benchmarking framework."""

import pytest
from typing import Generator, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging


@dataclass
class BenchmarkMetrics:
    """Structured benchmark metrics collector."""
    duration_ms: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    engine_response_time_ms: float = 0.0
    engine_tokens_generated: int = 0
    engine_tokens_per_second: float = 0.0
    engine_cost_usd: float = 0.0
    engine_cost_per_token: float = 0.0
    engine_latency_ms: float = 0.0
    engine_throughput_tokens_per_second: float = 0.0
    engine_context_window_used: int = 0
    engine_context_window_total: int = 0
    engine_temperature: float = 0.0
    engine_top_p: float = 0.0
    engine_n: int = 1
    engine_stop_sequences: List[str] = field(default_factory=list)
    engine_max_tokens: int = 0
    engine_model_name: str = ""
    engine_error: str = ""
    engine_success: bool = True


@dataclass
class LLMConfig:
    """LLM engine configuration."""
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 4096
    n: int = 1
    stop_sequences: List[str] = field(default_factory=list)
    streaming: bool = True
    timeout: int = 120
    context_window: int = 4096
    debug: bool = False
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class AppConfig:
    """Application configuration."""
    db_url: str = "sqlite:///./benchmark.db"
    cache_dir: str = ".cache"
    log_level: str = "INFO"
    max_memory_mb: int = 8192
    max_engine_concurrent: int = 10
    corpus_max_size_mb: int = 1024
    benchmark_timeout_seconds: int = 3600
    enable_metrics: bool = True
    enable_tracing: bool = False


@pytest.fixture
def logger() -> logging.Logger:
    """Create a structured logger for tests."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler("test_output.log")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger


@pytest.fixture
def benchmark_metrics() -> Generator[BenchmarkMetrics, None, None]:
    """Fixture to track benchmark metrics."""
    metrics = BenchmarkMetrics()
    try:
        yield metrics
    finally:
        metrics.end_time = datetime.now()
        metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
        metrics.engine_tokens_per_second = (
            metrics.engine_tokens_generated / (metrics.duration_ms / 1000)
            if metrics.duration_ms > 0
            else 0
        )
        metrics.engine_cost_per_token = (
            metrics.engine_cost_usd / metrics.engine_tokens_generated
            if metrics.engine_tokens_generated > 0
            else 0
        )
        metrics.engine_throughput_tokens_per_second = (
            metrics.engine_tokens_per_second / (metrics.engine_latency_ms / 1000)
            if metrics.engine_latency_ms > 0
            else 0
        )


@pytest.fixture
def config() -> Generator[AppConfig, None, None]:
    """Fixture to provide application configuration."""
    config = AppConfig()
    yield config
    config.cleanup()


@pytest.fixture
def clean_cache(tmp_path: pytest.TempPathFactory) -> Generator[str, None, None]:
    """Create a clean cache directory for each test."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    yield str(cache_dir)


@pytest.fixture
def mock_engine_response() -> Dict[str, Any]:
    """Mock response for testing."""
    return {
        "id": "test-response-123",
        "model": "test-model",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response",
                    "function_call": None,
                    "tool_calls": None,
                },
                "finish_reason": "stop",
                "logprobs": None,
                "index": 0,
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 50,
            "total_tokens": 60,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 10,
            "completion_cache_hit_tokens": 0,
            "completion_cache_miss_tokens": 50,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 0,
        },
    }


class MockEngine:
    """Mock LLM engine for testing."""
    
    def __init__(self, model: str = "test-model"):
        self.model = model
        self.config = LLMConfig(model=model)
    
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        config: LLMConfig,
    ) -> Dict[str, Any]:
        """Simulate LLM generation."""
        await asyncio.sleep(0.01)  # Simulate latency
        return mock_engine_response()
    
    async def astream_generate(
        self,
        messages: List[Dict[str, Any]],
        config: LLMConfig,
    ) -> Iterator[Dict[str, Any]]:
        """Simulate streaming generation."""
        for i in range(50):
            yield {
                "id": "test-response-123",
                "model": "test-model",
                "choices": [
                    {
                        "delta": {"content": f"Token {i}"},
                        "finish_reason": None,
                        "logprobs": None,
                        "index": 0,
                    }
                ],
                "usage": None,
            }


@pytest.fixture
def mock_engine() -> Generator[MockEngine, None, None]:
    """Fixture to provide a mock LLM engine."""
    engine = MockEngine()
    yield engine
    engine.cleanup()


@pytest.fixture
def sample_corpus() -> Generator[List[Dict[str, Any]], None, None]:
    """Sample corpus for testing."""
    corpus = [
        {
            "id": "doc-1",
            "title": "Introduction",
            "content": "This is the introduction section of the document. "
                     "It contains background information and context. "
                     "The document discusses various aspects of the topic. "
                     "Section one provides foundational knowledge. "
                     "Section two expands on the initial concepts. "
                     "Section three delves deeper into technical details. "
                     "Section four covers practical applications. "
                     "Section five presents case studies and examples. "
                     "Section six discusses future directions. "
                     "Section seven concludes with summary points. "
                     "Section eight provides references and citations. "
                     "Section nine contains appendices. "
                     "Section ten offers supplementary information.",
            "metadata": {
                "author": "Test Author",
                "date": "2024-01-01",
                "source": "test",
                "language": "en",
                "word_count": 150,
            },
        },
        {
            "id": "doc-2",
            "title": "Methodology",
            "content": "This section describes the methodology used in the research. "
                     "The approach employs quantitative methods to analyze the data. "
                     "Data was collected through surveys and interviews. "
                     "Statistical analysis was performed using standard techniques. "
                     "The sample size was 1000 participants. "
                     "Data was analyzed over a period of 12 months. "
                     "Results were validated through peer review. "
                     "The methodology section provides transparency. "
                     "Reproducibility was ensured through detailed documentation. "
                     "Ethical considerations were addressed throughout.",
            "metadata": {
                "author": "Research Team",
                "date": "2024-01-15",
                "source": "research",
                "language": "en",
                "word_count": 120,
            },
        },
        {
            "id": "doc-3",
            "title": "Results",
            "content": "The results of our analysis are presented below. "
                     "Key findings include significant improvements in performance. "
                     "Metrics show a 25% increase in efficiency. "
                     "User satisfaction scores improved by 15 points. "
                     "Cost reduction was achieved through optimization. "
                     "The data supports our hypothesis. "
                     "Statistical significance was confirmed at p < 0.05. "
                     "Visualizations illustrate the trends. "
                     "Comparative analysis shows clear differentiation. "
                     "Longitudinal study confirms sustainability.",
            "metadata": {
                "author": "Analysis Team",
                "date": "2024-02-01",
                "source": "analysis",
                "language": "en",
                "word_count": 130,
            },
        },
    ]
    yield corpus


@pytest.fixture
def sample_challenges() -> Generator[List[Dict[str, Any]], None, None]:
    """Sample challenges for testing."""
    challenges = [
        {
            "id": "challenge-1",
            "name": "Complex Reasoning",
            "description": "Test the model's ability to perform multi-step reasoning",
            "difficulty": "hard",
            "max_tokens": 2048,
            "timeout_seconds": 60,
            "tags": ["reasoning", "math", "logic"],
        },
        {
            "id": "challenge-2",
            "name": "Code Generation",
            "description": "Test code generation capabilities",
            "difficulty": "medium",
            "max_tokens": 4096,
            "timeout_seconds": 120,
            "tags": ["code", "programming", "python"],
        },
        {
            "id": "challenge-3",
            "name": "Creative Writing",
            "description": "Test creative writing capabilities",
            "difficulty": "easy",
            "max_tokens": 1024,
            "timeout_seconds": 30,
            "tags": ["creative", "writing", "narrative"],
        },
    ]
    yield challenges


@pytest.fixture
def sample_tasks() -> Generator[List[Dict[str, Any]], None, None]:
    """Sample tasks for testing."""
    tasks = [
        {
            "id": "task-1",
            "name": "Summarization",
            "description": "Summarize the given text",
            "type": "text",
            "input": None,
            "output": "string",
            "difficulty": "easy",
            "max_tokens": 512,
            "timeout_seconds": 30,
            "tags": ["summarization", "reading"],
        },
        {
            "id": "task-2",
            "name": "Classification",
            "description": "Classify sentiment in text",
            "type": "text",
            "input": "string",
            "output": "string",
            "difficulty": "medium",
            "max_tokens": 256,
            "timeout_seconds": 60,
            "tags": ["nlp", "classification"],
        },
        {
            "id": "task-3",
            "name": "Code Translation",
            "description": "Translate code between languages",
            "type": "code",
            "input": "string",
            "output": "string",
            "difficulty": "hard",
            "max_tokens": 2048,
            "timeout_seconds": 120,
            "tags": ["code", "translation"],
        },
    ]
    yield tasks


@pytest.fixture
def sample_engines() -> Generator[List[Dict[str, Any]], None, None]:
    """Sample engines for testing."""
    engines = [
        {
            "id": "engine-1",
            "name": "OpenAI GPT-4",
            "type": "openai",
            "model": "gpt-4",
            "config": {
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "status": "active",
            "cost_per_token": 0.03,
            "latency_ms": 500,
        },
        {
            "id": "engine-2",
            "name": "Local Llama",
            "type": "local",
            "model": "llama-3-8b",
            "config": {
                "temperature": 0.5,
                "max_tokens": 2048,
            },
            "status": "active",
            "cost_per_token": 0.0,
            "latency_ms": 100,
        },
        {
            "id": "engine-3",
            "name": "Anthropic Claude",
            "type": "anthropic",
            "model": "claude-3",
            "config": {
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            "status": "inactive",
            "cost_per_token": 0.05,
            "latency_ms": 800,
        },
    ]
    yield engines


@pytest.fixture
def sample_results() -> Generator[List[Dict[str, Any]], None, None]:
    """Sample results for testing."""
    results = [
        {
            "id": "result-1",
            "challenge_id": "challenge-1",
            "engine_id": "engine-1",
            "task_id": "task-1",
            "input": "Explain quantum computing in simple terms",
            "output": "Quantum computing is like having super-powered computers "
                    "that can solve certain problems much faster than regular computers. "
                    "They use quantum bits (qubits) that can be in multiple states at once. "
                    "This allows them to explore many possibilities simultaneously.",
            "metrics": {
                "tokens_used": 65,
                "tokens_generated": 52,
                "time_ms": 150,
                "cost_usd": 0.00195,
            },
            "quality_score": 0.92,
            "safety_score": 0.98,
            "accuracy_score": 0.89,
        },
        {
            "id": "result-2",
            "challenge_id": "challenge-2",
            "engine_id": "engine-2",
            "task_id": "task-2",
            "input": "Write a function to reverse a string",
            "output": "def reverse_string(s: str) -> str:\n    "
                    "    return s[::-1]\n\n# Example usage:\n# result = reverse_string('hello')\n# print(result)  # Output: 'olleh'",
            "metrics": {
                "tokens_used": 85,
                "tokens_generated": 78,
                "time_ms": 45,
                "cost_usd": 0.0,
            },
            "quality_score": 0.95,
            "safety_score": 1.0,
            "accuracy_score": 0.98,
        },
    ]
    yield results


class TestCleanup:
    """Context manager for test cleanup operations."""
    
    def __init__(self, cleanup_tasks: List[Any] = None):
        self.cleanup_tasks = cleanup_tasks or []
        self.tasks = []
    
    async def __aenter__(self):
        for task in self.cleanup_tasks:
            if hasattr(task, 'aclose'):
                self.tasks.append(task.aclose())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for task in self.tasks:
            await task


@pytest.fixture
def cleanup_context() -> Generator[TestCleanup, None, None]:
    """Context manager for async cleanup."""
    yield TestCleanup()
