"""Unit tests for engine implementations."""

import pytest
from unittest.mock import MagicMock, patch
from local_llm_benchmark.engines.base import Engine
from local_llm_benchmark.engines.stub import StubEngine
from local_llm_benchmark.config import EngineConfig


class TestStubEngine:
    """Unit tests for StubEngine."""
    
    def test_init(self):
        """Test StubEngine initialization."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        assert engine.config.name == "stub"
        assert engine.config.model == "stub-model"
    
    def test_list_models_empty(self):
        """Test that list_models returns empty list."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        models = engine.list_models()
        assert isinstance(models, list)
        assert len(models) == 0
    
    def test_chat_default_response(self):
        """Test default chat response."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        messages = [{"role": "user", "content": "Hello"}]
        response = engine.chat(messages)
        assert "choices" in response
        assert len(response["choices"]) > 0
    
    def test_chat_with_custom_tokens(self):
        """Test chat with custom max_tokens."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        messages = [{"role": "user", "content": "Test"}]
        response = engine.chat(messages, max_tokens=1024)
        assert response["choices"][0]["message"]["content"] == "test"  # Deterministic
    
    def test_chat_streaming(self):
        """Test streaming chat response."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        messages = [{"role": "user", "content": "Test"}]
        stream = engine.chat(messages, stream=True)
        assert hasattr(stream, "__aiter__")
    
    def test_supports_list_models(self):
        """Test supports_list_models returns False."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        assert engine.supports_list_models() == False
    
    def test_serve(self):
        """Test serve method."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        engine.serve()
        assert True
    
    def test_unload_model(self):
        """Test unload_model method."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        engine.unload_model()
        assert True
    
    def test_close(self):
        """Test close method."""
        config = EngineConfig(name="stub", base_url="http://stub", model="stub-model")
        engine = StubEngine(config)
        engine.close()
        assert True


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


class TestBaseEngine:
    """Unit tests for base Engine class."""
    
    def test_abstract_class(self):
        """Test that Engine is abstract."""
        with pytest.raises(TypeError):
            Engine()
    
    def test_required_methods(self):
        """Test that required methods exist."""
        engine = MagicMock(spec=Engine)
        assert hasattr(engine, "supports_list_models")
        assert hasattr(engine, "list_models")
        assert hasattr(engine, "chat")
        assert hasattr(engine, "serve")
        assert hasattr(engine, "unload_model")
        assert hasattr(engine, "close")
