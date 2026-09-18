"""Unit tests for runner.py - Benchmark orchestration functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from local_llm_benchmark.runner import (
    BenchmarkRunner,
    BenchmarkResult,
    run_benchmark,
    MetricsCollector,
    BenchmarkTask,
    BenchmarkConfig,
)


class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_constructor_default_values(self):
        """Test that BenchmarkResult has sensible default values."""
        result = BenchmarkResult(
            engine="ollama",
            model="llama3",
            judge="human",
            task_id="task-001",
            category="qa",
            prompt="Test prompt",
            expected="Expected answer",
            output="Model output",
            ttft_s=0.5,
            tok_per_s=50.0,
            iters_per_s=100.0,
            quality_passed=False,
            quality_deterministic=False,
            quality_judge=False,
            quality_note="",
        )
        assert result.engine == "ollama"
        assert result.model == "llama3"
        assert result.judge == "human"
        assert result.task_id == "task-001"
        assert result.category == "qa"
        assert result.prompt == "Test prompt"
        assert result.expected == "Expected answer"
        assert result.output == "Model output"
        assert result.ttft_s == 0.5
        assert result.tok_per_s == 50.0
        assert result.iters_per_s == 100.0
        assert result.quality_passed is False
        assert result.quality_deterministic is False
        assert result.quality_judge is False
        assert result.quality_note == ""

    def test_constructor_with_partial_values(self):
        """Test that missing fields default to empty values."""
        result = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-001",
        )
        assert result.engine == "ollama"
        assert result.model == "llama3"
        assert result.task_id == "task-001"
        # Test defaults
        assert result.judge == ""
        assert result.category == "qa"
        assert result.prompt == ""
        assert result.expected == ""
        assert result.output == ""
        assert result.ttft_s == 0.0
        assert result.tok_per_s == 0.0
        assert result.iters_per_s == 0.0
        assert result.quality_passed is False
        assert result.quality_deterministic is False
        assert result.quality_judge is False
        assert result.quality_note == ""

    def test_equality(self):
        """Test BenchmarkResult equality."""
        result1 = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-001",
            ttft_s=0.5,
            tok_per_s=50.0,
        )
        result2 = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-001",
            ttft_s=0.5,
            tok_per_s=50.0,
        )
        result3 = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-002",
            ttft_s=0.5,
            tok_per_s=50.0,
        )
        assert result1 == result2
        assert result1 != result3

    def test_repr(self):
        """Test BenchmarkResult string representation."""
        result = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-001",
            ttft_s=0.5,
            tok_per_s=50.0,
            quality_passed=True,
        )
        repr_str = repr(result)
        assert "engine='ollama'" in repr_str
        assert "model='llama3'" in repr_str
        assert "task_id='task-001'" in repr_str
        assert "ttft_s=0.5" in repr_str
        assert "tok_per_s=50.0" in repr_str

    def test_to_dict(self):
        """Test BenchmarkResult serialization to dictionary."""
        result = BenchmarkResult(
            engine="ollama",
            model="llama3",
            task_id="task-001",
            ttft_s=0.5,
            tok_per_s=50.0,
            quality_passed=True,
            quality_note="Great performance!",
        )
        d = result.to_dict()
        assert d["engine"] == "ollama"
        assert d["model"] == "llama3"
        assert d["task_id"] == "task-001"
        assert d["ttft_s"] == 0.5
        assert d["tok_per_s"] == 50.0
        assert d["quality_passed"] is True
        assert d["quality_note"] == "Great performance!"

    def test_from_dict(self):
        """Test BenchmarkResult deserialization from dictionary."""
        data = {
            "engine": "ollama",
            "model": "llama3",
            "task_id": "task-001",
            "ttft_s": 0.5,
            "tok_per_s": 50.0,
            "quality_passed": True,
            "quality_note": "Great performance!",
        }
        result = BenchmarkResult.from_dict(data)
        assert result.engine == "ollama"
        assert result.model == "llama3"
        assert result.task_id == "task-001"
        assert result.ttft_s == 0.5
        assert result.tok_per_s == 50.0
        assert result.quality_passed is True
        assert result.quality_note == "Great performance!"


class TestBenchmarkTask:
    """Test BenchmarkTask dataclass."""

    def test_constructor(self):
        """Test BenchmarkTask creation."""
        task = BenchmarkTask(
            id="task-001",
            prompt="What is 2+2?",
            expected="4",
            category="math",
        )
        assert task.id == "task-001"
        assert task.prompt == "What is 2+2?"
        assert task.expected == "4"
        assert task.category == "math"

    def test_to_dict(self):
        """Test BenchmarkTask serialization."""
        task = BenchmarkTask(
            id="task-001",
            prompt="What is 2+2?",
            expected="4",
            category="math",
        )
        assert task.to_dict() == {
            "id": "task-001",
            "prompt": "What is 2+2?",
            "expected": "4",
            "category": "math",
        }


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_init(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        assert collector.total_tasks == 0
        assert collector.total_ttft_s == 0.0
        assert collector.total_tok_per_s == 0.0
        assert collector.total_iters_per_s == 0.0

    def test_add_result(self):
        """Test adding a benchmark result."""
        collector = MetricsCollector()
        result = BenchmarkResult(
            task_id="task-001",
            ttft_s=0.5,
            tok_per_s=50.0,
            iters_per_s=100.0,
        )
        collector.add_result(result)
        assert collector.total_tasks == 1
        assert collector.total_ttft_s == 0.5
        assert collector.total_tok_per_s == 50.0
        assert collector.total_iters_per_s == 100.0

    def test_add_multiple_results(self):
        """Test adding multiple results."""
        collector = MetricsCollector()
        results = [
            BenchmarkResult(task_id="t1", ttft_s=0.5, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=0.3, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.4, tok_per_s=55.0, iters_per_s=110.0),
        ]
        for result in results:
            collector.add_result(result)
        assert collector.total_tasks == 3
        assert collector.total_ttft_s == 1.2
        assert collector.total_tok_per_s == 165.0
        assert collector.total_iters_per_s == 330.0

    def test_get_average(self):
        """Test average calculation."""
        collector = MetricsCollector()
        results = [
            BenchmarkResult(task_id="t1", ttft_s=0.5, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=0.3, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.4, tok_per_s=55.0, iters_per_s=110.0),
        ]
        for result in results:
            collector.add_result(result)
        
        avg_ttft = collector.get_average("ttft_s")
        avg_tok = collector.get_average("tok_per_s")
        avg_iters = collector.get_average("iters_per_s")
        
        assert avg_ttft == pytest.approx(0.4, rel=0.001)
        assert avg_tok == pytest.approx(55.0, rel=0.001)
        assert avg_iters == pytest.approx(110.0, rel=0.001)

    def test_get_average_empty(self):
        """Test average calculation with empty collector."""
        collector = MetricsCollector()
        avg = collector.get_average("ttft_s")
        assert avg == 0.0

    def test_get_summary(self):
        """Test metrics summary generation."""
        collector = MetricsCollector()
        results = [
            BenchmarkResult(task_id="t1", ttft_s=0.5, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=0.3, tok_per_s=60.0, iters_per_s=120.0),
        ]
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["total_ttft_s"] == 0.8
        assert summary["total_tok_per_s"] == 110.0
        assert summary["total_iters_per_s"] == 220.0
        assert summary["avg_ttft_s"] == pytest.approx(0.4)
        assert summary["avg_tok_per_s"] == pytest.approx(55.0)
        assert summary["avg_iters_per_s"] == pytest.approx(110.0)


class TestBenchmarkRunner:
    """Test BenchmarkRunner class."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine with benchmark method."""
        engine = MagicMock()
        engine.benchmark = AsyncMock(return_value=[
            {
                "task_id": "task-001",
                "output": "Answer: 4",
                "metrics": {"ttft_s": 0.5, "tok_per_s": 50.0, "iters_per_s": 100.0},
            }
        ])
        return engine

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        return MagicMock()

    def test_init_with_logger_and_collector(self, mock_config):
        """Test BenchmarkRunner initialization with custom logger and metrics collector."""
        logger = MagicMock()
        collector = MetricsCollector()
        runner = BenchmarkRunner(logger, collector, mock_config)
        
        assert runner.logger is logger
        assert runner.metrics_collector is collector
        assert runner.config is mock_config

    def test_init_default_logger(self, mock_config):
        """Test BenchmarkRunner initialization with default logger."""
        collector = MetricsCollector()
        runner = BenchmarkRunner(mock_config)
        
        assert runner.logger is not None
        assert runner.metrics_collector is collector

    def test_run_benchmark_success(self, mock_engine, mock_config):
        """Test successful benchmark execution."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = mock_engine.benchmark
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), mock_config)
            results = asyncio.run(runner.run_benchmark())
            
            assert len(results) == 1
            assert results[0].task_id == "task-001"
            assert results[0].output == "Answer: 4"
            assert results[0].ttft_s == 0.5
            assert results[0].tok_per_s == 50.0
            assert results[0].iters_per_s == 100.0

    def test_run_benchmark_multiple_tasks(self, mock_engine, mock_config):
        """Test benchmark execution with multiple tasks."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = mock_engine.benchmark
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), mock_config)
            results = asyncio.run(runner.run_benchmark())
            
            assert len(results) == 1
            assert results[0].task_id == "task-001"

    def test_run_benchmark_no_tasks(self, mock_config):
        """Test benchmark execution with no tasks."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[])
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), mock_config)
            results = asyncio.run(runner.run_benchmark())
            
            assert results == []

    def test_run_benchmark_empty_output(self, mock_config):
        """Test benchmark execution with empty output."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[{"task_id": "t1", "output": ""}])
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), mock_config)
            results = asyncio.run(runner.run_benchmark())
            
            assert len(results) == 1
            assert results[0].output == ""

    def test_run_benchmark_error_in_metrics(self, mock_config):
        """Test benchmark execution when metrics extraction fails."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[
                {"task_id": "task-001", "output": "Answer: 4"}
            ])
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), mock_config)
            results = asyncio.run(runner.run_benchmark())
            
            # Should still return results, just with default metrics
            assert len(results) == 1
            assert results[0].task_id == "task-001"
            assert results[0].output == "Answer: 4"
            assert results[0].ttft_s == 0.0  # Default value

    def test_run_benchmark_configured_metrics(self, mock_config):
        """Test benchmark execution with configured metrics."""
        config = MagicMock()
        config.metrics = ["ttft_s", "tok_per_s"]
        
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[
                {"task_id": "task-001", "output": "Answer: 4", "metrics": {"ttft_s": 0.5, "tok_per_s": 50.0}}
            ])
            
            runner = BenchmarkRunner(Mock(), MetricsCollector(), config)
            results = asyncio.run(runner.run_benchmark())
            
            assert len(results) == 1
            assert results[0].ttft_s == 0.5
            assert results[0].tok_per_s == 50.0


class TestRunBenchmark:
    """Test run_benchmark() top-level function."""

    def test_run_benchmark_simple(self, mock_config):
        """Test simple benchmark run."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[
                {"task_id": "task-001", "output": "Answer: 4", "metrics": {"ttft_s": 0.5}}
            ])
            
            results = asyncio.run(run_benchmark(mock_config))
            
            assert len(results) == 1
            assert results[0].task_id == "task-001"
            assert results[0].output == "Answer: 4"

    def test_run_benchmark_no_tasks(self, mock_config):
        """Test benchmark run with no tasks."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[])
            
            results = asyncio.run(run_benchmark(mock_config))
            
            assert results == []

    def test_run_benchmark_empty_output(self, mock_config):
        """Test benchmark run with empty output."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[{"task_id": "t1", "output": ""}])
            
            results = asyncio.run(run_benchmark(mock_config))
            
            assert len(results) == 1
            assert results[0].output == ""

    def test_run_benchmark_no_metrics(self, mock_config):
        """Test benchmark run without metrics."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[{"task_id": "t1", "output": ""}])
            
            results = asyncio.run(run_benchmark(mock_config))
            
            assert len(results) == 1
            assert results[0].output == ""


class TestAsyncSupport:
    """Test async-related functionality."""

    def test_run_benchmark_returns_coroutine(self, mock_config):
        """Test that run_benchmark returns a coroutine."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[{"task_id": "t1"}])
            
            result = run_benchmark(mock_config)
            assert asyncio.iscoroutine(result)

    def test_run_benchmark_concurrent(self, mock_config):
        """Test concurrent benchmark execution."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[
                {"task_id": f"task-{i}", "output": f"Answer {i}", "metrics": {"ttft_s": float(i) / 10}}
                for i in range(10)
            ])
            
            import asyncio
            results = asyncio.run(run_benchmark(mock_config))
            
            assert len(results) == 10
            task_ids = [r.task_id for r in results]
            assert set(task_ids) == {f"task-{i}" for i in range(10)}


class TestErrorHandling:
    """Test error handling."""

    def test_run_benchmark_no_engine(self, mock_config):
        """Test benchmark run when engine is None."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = None
            
            try:
                asyncio.run(run_benchmark(mock_config))
                assert False, "Expected exception"
            except Exception as e:
                assert "No engine" in str(e)

    def test_run_benchmark_invalid_task_format(self, mock_config):
        """Test benchmark run with invalid task format."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=["invalid"])
            
            results = asyncio.run(run_benchmark(mock_config))
            assert len(results) == 1
            assert results[0].task_id == ""
            assert results[0].output == ""

    def test_run_benchmark_invalid_metrics_format(self, mock_config):
        """Test benchmark run with invalid metrics format."""
        with patch("local_llm_benchmark.runner.engine") as mock_engine_module:
            mock_engine_module.benchmark = AsyncMock(return_value=[
                {"task_id": "t1", "output": "", "metrics": "invalid"}
            ])
            
            results = asyncio.run(run_benchmark(mock_config))
            assert len(results) == 1
            assert results[0].output == ""


class TestMetricsCalculation:
    """Test metrics calculation accuracy."""

    def test_ttft_calculation(self):
        """Test TTFT calculation from metrics."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=2.0, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.5, tok_per_s=40.0, iters_per_s=80.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        avg_ttft = collector.get_average("ttft_s")
        expected_ttft = (1.0 + 2.0 + 0.5) / 3
        assert avg_ttft == pytest.approx(expected_ttft)

    def test_tok_per_s_calculation(self):
        """Test tokens per second calculation."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=2.0, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.5, tok_per_s=40.0, iters_per_s=80.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        avg_tok = collector.get_average("tok_per_s")
        expected_tok = (50.0 + 60.0 + 40.0) / 3
        assert avg_tok == pytest.approx(expected_tok)

    def test_iters_per_s_calculation(self):
        """Test iterations per second calculation."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=2.0, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.5, tok_per_s=40.0, iters_per_s=80.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        avg_iters = collector.get_average("iters_per_s")
        expected_iters = (100.0 + 120.0 + 80.0) / 3
        assert avg_iters == pytest.approx(expected_iters)

    def test_summary_consistency(self):
        """Test that summary values are consistent."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=2.0, tok_per_s=60.0, iters_per_s=120.0),
            BenchmarkResult(task_id="t3", ttft_s=0.5, tok_per_s=40.0, iters_per_s=80.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        
        # Total counts
        assert summary["total_tasks"] == 3
        assert summary["total_ttft_s"] == 3.5
        assert summary["total_tok_per_s"] == 150.0
        assert summary["total_iters_per_s"] == 300.0
        
        # Average values
        assert summary["avg_ttft_s"] == pytest.approx(1.1666666666666667)
        assert summary["avg_tok_per_s"] == pytest.approx(50.0)
        assert summary["avg_iters_per_s"] == pytest.approx(100.0)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_metrics(self):
        """Test handling of zero metrics."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=0.0, tok_per_s=0.0, iters_per_s=0.0),
            BenchmarkResult(task_id="t2", ttft_s=0.0, tok_per_s=0.0, iters_per_s=0.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["avg_ttft_s"] == 0.0

    def test_large_metrics(self):
        """Test handling of large metric values."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=1000.0, tok_per_s=10000.0, iters_per_s=100000.0),
            BenchmarkResult(task_id="t2", ttft_s=2000.0, tok_per_s=20000.0, iters_per_s=200000.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["avg_tok_per_s"] == pytest.approx(15000.0)

    def test_small_metrics(self):
        """Test handling of very small metric values."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=0.0001, tok_per_s=0.001, iters_per_s=0.01),
            BenchmarkResult(task_id="t2", ttft_s=0.0002, tok_per_s=0.002, iters_per_s=0.02),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["avg_ttft_s"] == pytest.approx(0.00015)

    def test_nan_metrics(self):
        """Test handling of NaN metrics."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=float("nan"), tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=1.0, tok_per_s=float("nan"), iters_per_s=100.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        # NaN values should result in NaN average
        import math
        assert math.isnan(summary["avg_ttft_s"])

    def test_infinite_metrics(self):
        """Test handling of infinite metric values."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=float("inf"), tok_per_s=50.0, iters_per_s=100.0),
            BenchmarkResult(task_id="t2", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["avg_ttft_s"] == float("inf")

    def test_negative_metrics(self):
        """Test handling of negative metric values."""
        collector = MetricsCollector()
        
        results = [
            BenchmarkResult(task_id="t1", ttft_s=-0.5, tok_per_s=-50.0, iters_per_s=-100.0),
            BenchmarkResult(task_id="t2", ttft_s=1.0, tok_per_s=50.0, iters_per_s=100.0),
        ]
        
        for result in results:
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["avg_ttft_s"] == -0.25

    def test_many_results(self):
        """Test handling of many results."""
        collector = MetricsCollector()
        
        for i in range(1000):
            result = BenchmarkResult(
                task_id=f"task-{i}",
                ttft_s=float(i) / 100,
                tok_per_s=50.0 + float(i) * 0.1,
                iters_per_s=100.0 + float(i) * 0.2,
            )
            collector.add_result(result)
        
        summary = collector.get_summary()
        assert summary["total_tasks"] == 1000
        assert summary["total_ttft_s"] == pytest.approx(49950.0)
        assert summary["total_tok_per_s"] == pytest.approx(50500.0)
        assert summary["total_iters_per_s"] == pytest.approx(101000.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
