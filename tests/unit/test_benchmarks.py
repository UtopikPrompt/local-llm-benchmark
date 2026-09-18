"""Unit tests for benchmark modules."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import anyio
from local_llm_benchmark.config import BenchmarkConfig, EngineConfig, JudgeConfig
from local_llm_benchmark.runner import run_benchmark
from local_llm_benchmark.tasks.corpus import Task


class TestBenchmarkConfig:
    """Unit tests for BenchmarkConfig."""
    
    def test_default_config(self):
        """Test default benchmark configuration."""
        config = BenchmarkConfig(tasks=".")
        assert config.tasks == "."
        assert config.timeout == 60.0
        assert config.max_concurrent == 1
    
    def test_custom_config(self):
        """Test custom benchmark configuration."""
        config = BenchmarkConfig(
            tasks=".",
            timeout=120.0,
            max_concurrent=4
        )
        assert config.timeout == 120.0
        assert config.max_concurrent == 4
    
    def test_engine_config(self):
        """Test engine configuration."""
        engines = [
            EngineConfig(name="test-1", base_url="http://localhost:11434", model="llama3:8b"),
            EngineConfig(name="test-2", base_url="http://localhost:12345", model="mistral-small")
        ]
        config = BenchmarkConfig(engines=engines)
        assert len(config.engines) == 2
        assert config.engines[0].name == "test-1"
        assert config.engines[1].name == "test-2"
    
    def test_judge_config(self):
        """Test judge configuration."""
        judges = [
            JudgeConfig(name="quality", threshold=0.8),
            JudgeConfig(name="speed", threshold=10000)
        ]
        config = BenchmarkConfig(judges=judges)
        assert len(config.judges) == 2
        assert config.judges[0].name == "quality"
        assert config.judges[0].threshold == 0.8


class TestTaskSelection:
    """Unit tests for task selection."""
    
    def test_select_tasks_default_corpus(self, mock_config):
        """Test task selection from default corpus."""
        tasks = run_benchmark._select_tasks(mock_config)
        assert len(tasks) > 0
    
    def test_select_tasks_explicit_dir(self, tmp_path, mock_config):
        """Test task selection from explicit directory."""
        (tmp_path / "tasks.json").write_text(
            '{"id": "a", "category": "qa", "prompt": "a", "expected": "e"}'
        )
        config = BenchmarkConfig(tasks=str(tmp_path))
        tasks = run_benchmark._select_tasks(config)
        assert len(tasks) == 1
        assert tasks[0].id == "a"


class TestBenchmarkRunner:
    """Unit tests for benchmark runner."""
    
    @pytest.mark.asyncio
    async def test_run_benchmark_with_stub_engine(self, tmp_path):
        """Test running benchmark with stub engine."""
        # Create a simple task file
        task_file = tmp_path / "task.json"
        task_file.write_text(
            '{"id": "test-task", "category": "qa", "prompt": "What is 2+2?", "expected": "4"}'
        )
        
        # Create benchmark config with stub engine
        from local_llm_benchmark.config import EngineConfig
        config = BenchmarkConfig(
            tasks=str(tmp_path),
            engines=[EngineConfig(name="stub", base_url="http://stub", model="stub")]
        )
        
        # Run benchmark
        results = await run_benchmark(config)
        
        assert len(results) > 0
        assert "metrics" in results[0]
        assert "quality_score" in results[0]
    
    @pytest.mark.asyncio
    async def test_run_benchmark_error_handling(self, tmp_path):
        """Test benchmark error handling."""
        # Create task file
        task_file = tmp_path / "task.json"
        task_file.write_text(
            '{"id": "test-task", "category": "qa", "prompt": "Test", "expected": "answer"}'
        )
        
        # Config with stub engine
        config = BenchmarkConfig(
            tasks=str(tmp_path),
            engines=[EngineConfig(name="stub", base_url="http://stub", model="stub")]
        )
        
        # Should complete without error
        results = await run_benchmark(config)
        assert len(results) > 0
    
    def test_select_tasks_empty_corpus(self, mock_config):
        """Test task selection when corpus is empty."""
        config = BenchmarkConfig(tasks="nonexistent")
        tasks = run_benchmark._select_tasks(config)
        assert len(tasks) == 0


class TestEngineConfig:
    """Unit tests for EngineConfig."""
    
    def test_default_values(self):
        """Test EngineConfig default values."""
        config = EngineConfig(name="test")
        assert config.name == "test"
        assert config.base_url == "http://localhost"
        assert config.model == "default-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
    
    def test_custom_values(self):
        """Test EngineConfig custom values."""
        config = EngineConfig(
            name="custom",
            base_url="http://custom:8080",
            model="custom-model",
            temperature=0.5,
            max_tokens=2048
        )
        assert config.name == "custom"
        assert config.base_url == "http://custom:8080"
        assert config.model == "custom-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
    
    def test_all_fields(self):
        """Test EngineConfig with all fields."""
        config = EngineConfig(
            name="full",
            base_url="http://full:9999",
            model="full-model",
            api_key="secret",
            temperature=0.3,
            top_p=0.85,
            max_tokens=8192,
            n=2,
            stop_sequences=["<end>", "<stop>"],
            timeout=300,
            debug=True
        )
        assert config.name == "full"
        assert config.base_url == "http://full:9999"
        assert config.model == "full-model"
        assert config.temperature == 0.3
        assert config.top_p == 0.85
        assert config.max_tokens == 8192
        assert config.n == 2
        assert config.timeout == 300
        assert config.debug == True


class TestJudgeConfig:
    """Unit tests for JudgeConfig."""
    
    def test_default_values(self):
        """Test JudgeConfig default values."""
        config = JudgeConfig(name="test")
        assert config.name == "test"
        assert config.threshold == 0.7
    
    def test_custom_threshold(self):
        """Test custom threshold."""
        config = JudgeConfig(name="strict", threshold=0.95)
        assert config.name == "strict"
        assert config.threshold == 0.95
    
    def test_default_threshold(self):
        """Test default threshold is 0.7."""
        config = JudgeConfig(name="default")
        assert config.threshold == 0.7
