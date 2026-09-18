"""Unit tests for benchmark tasks."""

import pytest
from local_llm_benchmark.tasks.corpus import Task


class TestTask:
    """Unit tests for Task class."""
    
    def test_from_dict_basic(self):
        """Test Task creation from dict."""
        task_dict = {
            "id": "task-1",
            "category": "qa",
            "prompt": "What is the capital of France?",
            "expected": "Paris"
        }
        task = Task.from_dict(task_dict)
        assert task.id == "task-1"
        assert task.category == "qa"
        assert task.prompt == "What is the capital of France?"
        assert task.expected == "Paris"
    
    def test_from_dict_with_all_fields(self):
        """Test Task creation with all fields."""
        task_dict = {
            "id": "task-2",
            "category": "classification",
            "prompt": "Analyze sentiment of this text",
            "input": "string",
            "output": "string",
            "difficulty": "medium",
            "max_tokens": 1024,
            "timeout_seconds": 60,
            "tags": ["nlp", "sentiment"]
        }
        task = Task.from_dict(task_dict)
        assert task.id == "task-2"
        assert task.category == "classification"
        assert task.prompt == "Analyze sentiment of this text"
        assert task.input == "string"
        assert task.output == "string"
        assert task.difficulty == "medium"
        assert task.max_tokens == 1024
        assert task.timeout_seconds == 60
        assert task.tags == ["nlp", "sentiment"]
    
    def test_from_dict_defaults(self):
        """Test Task creation with default values."""
        task_dict = {
            "id": "task-3",
            "category": "text",
            "prompt": "Simple prompt"
        }
        task = Task.from_dict(task_dict)
        assert task.difficulty == "easy"
        assert task.max_tokens == 4096
        assert task.timeout_seconds == 120
        assert task.tags == []
    
    def test_to_dict(self):
        """Test Task serialization to dict."""
        task = Task(id="task-4", category="qa", prompt="Test prompt", expected="Test answer")
        task_dict = task.to_dict()
        assert task_dict["id"] == "task-4"
        assert task_dict["category"] == "qa"
        assert task_dict["prompt"] == "Test prompt"
        assert task_dict["expected"] == "Test answer"
    
    def test_parse_category_valid(self):
        """Test parsing valid category."""
        result = Task._parse_category("qa")
        assert result == "qa"
    
    def test_parse_category_valid_text(self):
        """Test parsing valid text category."""
        result = Task._parse_category("text")
        assert result == "text"
    
    def test_parse_category_valid_classification(self):
        """Test parsing valid classification category."""
        result = Task._parse_category("classification")
        assert result == "classification"
    
    def test_parse_category_unknown_raises(self):
        """Test parsing unknown category raises ValueError."""
        with pytest.raises(ValueError):
            Task._parse_category("unknown")
    
    def test_parse_category_empty_raises(self):
        """Test parsing empty category raises ValueError."""
        with pytest.raises(ValueError):
            Task._parse_category("")
    
    def test_parse_category_none_raises(self):
        """Test parsing None category raises ValueError."""
        with pytest.raises(ValueError):
            Task._parse_category(None)
    
    def test_category_parse_valid_qa(self):
        """Test QA category parsing."""
        result = Task._parse_category("qa")
        assert result == "qa"
    
    def test_difficulty_values(self):
        """Test difficulty level values."""
        assert Task.difficulty.easy == "easy"
        assert Task.difficulty.medium == "medium"
        assert Task.difficulty.hard == "hard"
    
    def test_comparison(self):
        """Test task comparison."""
        task1 = Task(id="t1", category="qa", prompt="prompt1", expected="answer1")
        task2 = Task(id="t2", category="qa", prompt="prompt2", expected="answer2")
        task3 = Task(id="t1", category="qa", prompt="prompt1", expected="answer1")
        
        assert task1 == task2  # Different prompts
        assert task1 != task3  # Same task
        assert task1.id == task3.id
        assert task1.prompt == task3.prompt
    
    def test_hash_equality(self):
        """Test that equal tasks have equal hashes."""
        task1 = Task(id="t1", category="qa", prompt="prompt1", expected="answer1")
        task2 = Task(id="t1", category="qa", prompt="prompt1", expected="answer1")
        assert hash(task1) == hash(task2)
    
    def test_repr(self):
        """Test task repr."""
        task = Task(id="task-5", category="qa", prompt="Test prompt", expected="Test answer")
        repr_str = repr(task)
        assert task.id in repr_str
        assert task.category in repr_str
        assert task.prompt in repr_str
