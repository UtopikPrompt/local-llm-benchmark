"""Unit tests for results.py - Data serialization and output."""

import pytest
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime
from local_llm_benchmark.results import (
    Row,
    CSV_COLUMNS,
    write_csv,
    write_json,
    write_report,
)


class TestMetrics:
    """Unit tests for Metrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = Metrics()
        assert metrics.duration_ms == 0.0
        assert metrics.engine_response_time_ms == 0.0
        assert metrics.engine_tokens_generated == 0
        assert metrics.engine_tokens_per_second == 0.0
        assert metrics.engine_cost_usd == 0.0
    
    def test_custom_metrics(self):
        """Test custom metrics."""
        metrics = Metrics(
            duration_ms=120000.0,
            engine_response_time_ms=15000.0,
            engine_tokens_generated=15000,
            engine_tokens_per_second=1000.0,
            engine_cost_usd=0.45,
            engine_latency_ms=500.0,
            engine_throughput_tokens_per_second=20.0
        )
        assert metrics.duration_ms == 120000.0
        assert metrics.engine_tokens_generated == 15000
        assert metrics.engine_cost_usd == 0.45


class TestRow:
    """Unit tests for Row dataclass."""
    
    def test_row_default_values(self):
        """Test Row with default values."""
        row = Row()
        assert row.engine == ""
        assert row.model == ""
        assert row.judge == ""
        assert row.task_id == ""
        assert row.category == "qa"
        assert row.prompt == ""
        assert row.expected == ""
        assert row.output == ""
        assert row.ttft_s == 0.0
        assert row.tok_per_s == 0.0
        assert row.iters_per_s == 0.0
        assert row.quality_passed == False
        assert row.quality_deterministic == False
        assert row.quality_judge == False
        assert row.quality_note == ""
    
    def test_row_full_construction(self):
        """Test Row with all fields set."""
        row = Row(
            engine="ollama",
            model="gemma4:e2b",
            judge="ollama",
            task_id="qa",
            category="qa",
            prompt="What is 2+2?",
            expected="4",
            output="4",
            ttft_s=0.1,
            tok_per_s=10.0,
            iters_per_s=100.0,
            quality_passed=True,
            quality_deterministic=True,
            quality_judge=True,
            quality_note="Excellent response",
        )
        assert row.engine == "ollama"
        assert row.model == "gemma4:e2b"
        assert row.judge == "ollama"
        assert row.task_id == "qa"
        assert row.category == "qa"
        assert row.prompt == "What is 2+2?"
        assert row.expected == "4"
        assert row.output == "4"
        assert row.ttft_s == 0.1
        assert row.tok_per_s == 10.0
        assert row.iters_per_s == 100.0
        assert row.quality_passed == True
        assert row.quality_deterministic == True
        assert row.quality_judge == True
        assert row.quality_note == "Excellent response"
    
    def test_row_to_dict(self):
        """Test Row.to_dict() method."""
        row = Row(
            engine="ollama",
            model="gemma4:e2b",
            task_id="qa",
            ttft_s=0.1,
            tok_per_s=10.0,
            quality_passed=True,
        )
        row_dict = row.to_dict()
        
        assert "engine" in row_dict
        assert "model" in row_dict
        assert "task_id" in row_dict
        assert "ttft_s" in row_dict
        assert "tok_per_s" in row_dict
        assert "quality_passed" in row_dict
        assert row_dict["engine"] == "ollama"
        assert row_dict["model"] == "gemma4:e2b"
        assert row_dict["quality_passed"] == True
    
    def test_row_repr(self):
        """Test Row.__repr__() method."""
        row = Row(engine="ollama", model="llama3")
        repr_str = repr(row)
        
        assert "Row" in repr_str
        assert "ollama" in repr_str
        assert "llama3" in repr_str


class TestCSV_COLUMNS:
    """Unit tests for CSV_COLUMNS tuple."""
    
    def test_columns_defined(self):
        """Test that CSV_COLUMNS is defined."""
        assert CSV_COLUMNS is not None
        assert len(CSV_COLUMNS) > 0
    
    def test_column_count(self):
        """Test that CSV_COLUMNS has correct number of columns."""
        assert len(CSV_COLUMNS) == 15
    
    def test_column_names(self):
        """Test all expected column names are present."""
        expected_columns = [
            "engine", "model", "judge", "task_id", "category",
            "prompt", "expected", "output", "ttft_s", "tok_per_s",
            "iters_per_s", "quality_passed", "quality_deterministic",
            "quality_judge", "quality_note"
        ]
        
        for col in expected_columns:
            assert col in CSV_COLUMNS, f"Column '{col}' not found in CSV_COLUMNS"
    
    def test_columns_sorted_alphabetically(self):
        """Test that CSV_COLUMNS is sorted alphabetically."""
        assert CSV_COLUMNS == tuple(sorted(CSV_COLUMNS))


class TestWriteCSV:
    """Unit tests for write_csv function."""
    
    def test_write_csv_empty_rows(self):
        """Test writing empty rows to CSV."""
        with patch('pathlib.Path') as mock_path:
            mock_path.open.return_value.__enter__.return_value.__exit__.return_value = None
            write_csv([], Path('empty.csv'))
    
    def test_write_csv_single_row(self):
        """Test writing a single row to CSV."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa", ttft_s=0.1)]
        
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_csv(rows, Path('test_output.csv'))
        
        # Verify file content
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'engine,model,judge,task_id,category,prompt,expected,output,ttft_s,' in content
        assert 'ollama,llama3,,,qa,,,' in content
        
        # Cleanup
        Path('test_output.csv').unlink()
    
    def test_write_csv_multiple_rows(self):
        """Test writing multiple rows to CSV."""
        rows = [
            Row(engine="ollama", model="llama3", task_id="qa", ttft_s=0.1, tok_per_s=10.0),
            Row(engine="llama.cpp", model="gemma2", task_id="qa", ttft_s=0.2, tok_per_s=8.0),
        ]
        
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_csv(rows, Path('test_output.csv'))
        
        # Verify file content
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["engine"] == "ollama"
        assert rows[1]["engine"] == "llama.cpp"
        
        # Cleanup
        Path('test_output.csv').unlink()
    
    def test_write_csv_extra_fields_ignored(self):
        """Test that extra fields in row are ignored."""
        rows = [Row(engine="ollama", model="llama3", extra_field="ignored")]
        
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_csv(rows, Path('test_output.csv'))
        
        # Verify file content
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert "extra_field" not in rows[0]
        
        # Cleanup
        Path('test_output.csv').unlink()
    
    def test_write_csv_unicode(self):
        """Test writing unicode characters in CSV."""
        rows = [Row(engine="ollama", model="llama3:中文", task_id="qa", prompt="你好")]
        
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_csv(rows, Path('test_output.csv'))
        
        # Verify file content
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "中文" in content
        
        # Cleanup
        Path('test_output.csv').unlink()


class TestWriteJSON:
    """Unit tests for write_json function."""
    
    def test_write_json_empty_rows(self):
        """Test writing empty rows to JSON."""
        with patch('pathlib.Path') as mock_path:
            mock_path.open.return_value.__enter__.return_value.__exit__.return_value = None
            write_json([], Path('empty.json'))
    
    def test_write_json_single_row(self):
        """Test writing a single row to JSON."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa", ttft_s=0.1, tok_per_s=10.0)]
        
        with open('test_output.json', 'w', encoding='utf-8') as f:
            write_json(rows, Path('test_output.json'))
        
        # Verify file content
        with open('test_output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["engine"] == "ollama"
        assert data[0]["model"] == "llama3"
        assert data[0]["ttft_s"] == 0.1
        
        # Cleanup
        Path('test_output.json').unlink()
    
    def test_write_json_multiple_rows(self):
        """Test writing multiple rows to JSON."""
        rows = [
            Row(engine="ollama", model="llama3", task_id="qa", ttft_s=0.1),
            Row(engine="llama.cpp", model="gemma2", task_id="qa", ttft_s=0.2),
        ]
        
        with open('test_output.json', 'w', encoding='utf-8') as f:
            write_json(rows, Path('test_output.json'))
        
        # Verify file content
        with open('test_output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data) == 2
        assert data[0]["engine"] == "ollama"
        assert data[1]["engine"] == "llama.cpp"
        
        # Cleanup
        Path('test_output.json').unlink()
    
    def test_write_json_indentation(self):
        """Test that JSON is properly indented."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa")]
        
        with open('test_output.json', 'w', encoding='utf-8') as f:
            write_json(rows, Path('test_output.json'))
        
        # Verify file content
        with open('test_output.json', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that content is indented (2 spaces)
        lines = content.split('\n')
        assert any(line.startswith('  ')) for line in lines
        
        # Cleanup
        Path('test_output.json').unlink()


class TestWriteReport:
    """Unit tests for write_report function."""
    
    def test_write_report_json(self):
        """Test writing report in JSON format."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa")]
        
        with open('test_output.json', 'w', encoding='utf-8') as f:
            write_report(rows, Path('test_output.json'), fmt="json")
        
        # Verify file content
        with open('test_output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["engine"] == "ollama"
        
        # Cleanup
        Path('test_output.json').unlink()
    
    def test_write_report_csv(self):
        """Test writing report in CSV format."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa")]
        
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_report(rows, Path('test_output.csv'), fmt="csv")
        
        # Verify file content
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'engine,model,judge,task_id' in content
        assert 'ollama,llama3,,,qa' in content
        
        # Cleanup
        Path('test_output.csv').unlink()
    
    def test_write_report_invalid_format(self):
        """Test that invalid format raises ValueError."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa")]
        
        with pytest.raises(ValueError, match="Unsupported format"):
            write_report(rows, Path('test_output.json'), fmt="xml")
    
    def test_write_report_case_insensitive_format(self):
        """Test that format parameter is case insensitive."""
        rows = [Row(engine="ollama", model="llama3", task_id="qa")]
        
        # Test uppercase format
        with open('test_output.csv', 'w', newline='', encoding='utf-8') as f:
            write_report(rows, Path('test_output.csv'), fmt="JSON")
        
        # Verify it wrote CSV
        with open('test_output.csv', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'engine,model,judge,task_id' in content
        
        # Cleanup
        Path('test_output.csv').unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

    
    def test_custom_metrics(self):
        """Test custom metrics."""
        metrics = Metrics(
            duration_ms=120000.0,
            engine_response_time_ms=15000.0,
            engine_tokens_generated=15000,
            engine_tokens_per_second=1000.0,
            engine_cost_usd=0.45,
            engine_latency_ms=500.0,
            engine_throughput_tokens_per_second=20.0
        )
        assert metrics.duration_ms == 120000.0
        assert metrics.engine_tokens_generated == 15000
        assert metrics.engine_cost_usd == 0.45
    
    def test_metrics_from_dict(self):
        """Test Metrics from dict."""
        metrics_dict = {
            "duration_ms": 100000.0,
            "engine_tokens_generated": 12000,
            "engine_cost_usd": 0.36
        }
        metrics = Metrics.from_dict(metrics_dict)
        assert metrics.duration_ms == 100000.0
        assert metrics.engine_tokens_generated == 12000
    
    def test_metrics_to_dict(self):
        """Test Metrics to dict."""
        metrics = Metrics(
            duration_ms=100000.0,
            engine_tokens_generated=12000,
            engine_cost_usd=0.36
        )
        metrics_dict = metrics.to_dict()
        assert metrics_dict["duration_ms"] == 100000.0
        assert metrics_dict["engine_tokens_generated"] == 12000
        assert metrics_dict["engine_cost_usd"] == 0.36
    
    def test_metrics_from_result(self):
        """Test extracting metrics from Result."""
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            input="Test input",
            output="Test output",
            metrics=Metrics(
                duration_ms=100000.0,
                engine_tokens_generated=12000,
                engine_cost_usd=0.36
            )
        )
        metrics = Metrics.from_result(result)
        assert metrics.duration_ms == 100000.0
        assert metrics.engine_tokens_generated == 12000


class TestResult:
    """Unit tests for Result dataclass."""
    
    def test_default_result(self):
        """Test default result values."""
        result = Result()
        assert result.id == ""
        assert result.challenge_id == ""
        assert result.engine_id == ""
        assert result.task_id == ""
        assert result.input == ""
        assert result.output == ""
        assert result.quality_score == 0.0
        assert result.safety_score == 0.0
        assert result.accuracy_score == 0.0
    
    def test_custom_result(self):
        """Test custom result."""
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            input="Test input",
            output="Test output",
            quality_score=0.92,
            safety_score=0.98,
            accuracy_score=0.89
        )
        assert result.id == "result-1"
        assert result.quality_score == 0.92
        assert result.safety_score == 0.98
    
    def test_result_from_dict(self):
        """Test Result from dict."""
        result_dict = {
            "id": "result-1",
            "challenge_id": "challenge-1",
            "engine_id": "engine-1",
            "task_id": "task-1",
            "input": "Test input",
            "output": "Test output",
            "quality_score": 0.92,
            "metrics": {
                "duration_ms": 100000.0,
                "engine_tokens_generated": 12000,
                "engine_cost_usd": 0.36
            }
        }
        result = Result.from_dict(result_dict)
        assert result.id == "result-1"
        assert result.quality_score == 0.92
    
    def test_result_to_dict(self):
        """Test Result to dict."""
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            input="Test input",
            output="Test output",
            quality_score=0.92,
            safety_score=0.98,
            accuracy_score=0.89
        )
        result_dict = result.to_dict()
        assert result_dict["id"] == "result-1"
        assert result_dict["quality_score"] == 0.92
        assert result_dict["safety_score"] == 0.98
        assert result_dict["accuracy_score"] == 0.89
    
    def test_result_from_metrics(self):
        """Test creating result from metrics."""
        metrics = Metrics(
            duration_ms=100000.0,
            engine_tokens_generated=12000,
            engine_cost_usd=0.36
        )
        result = Result.from_metrics(metrics)
        assert result.id == ""
        assert result.quality_score == 0.0
        assert result.safety_score == 0.0
        assert result.accuracy_score == 0.0
    
    def test_result_repr(self):
        """Test result repr."""
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92,
            safety_score=0.98
        )
        repr_str = repr(result)
        assert result.id in repr_str
        assert result.quality_score in repr_str
        assert result.safety_score in repr_str


class TestResultCollection:
    """Unit tests for Result collection."""
    
    def test_result_collection_init(self):
        """Test ResultCollection initialization."""
        collection = ResultCollection()
        assert len(collection) == 0
    
    def test_result_collection_append(self):
        """Test appending results."""
        collection = ResultCollection()
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92
        )
        collection.append(result)
        assert len(collection) == 1
        assert collection[0].id == "result-1"
    
    def test_result_collection_summary(self):
        """Test collection summary."""
        collection = ResultCollection()
        
        result1 = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92,
            safety_score=0.98
        )
        result2 = Result(
            id="result-2",
            challenge_id="challenge-1",
            engine_id="engine-2",
            task_id="task-2",
            quality_score=0.85,
            safety_score=0.95
        )
        result3 = Result(
            id="result-3",
            challenge_id="challenge-2",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.88,
            safety_score=0.97
        )
        
        collection.append(result1)
        collection.append(result2)
        collection.append(result3)
        
        summary = collection.summary()
        assert summary["total_results"] == 3
        assert summary["total_challenges"] == 2
        assert summary["total_engines"] == 2
        assert summary["avg_quality_score"] > 0.8
        assert summary["avg_safety_score"] > 0.9
    
    def test_result_collection_by_engine(self):
        """Test filtering results by engine."""
        collection = ResultCollection()
        
        result1 = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92
        )
        result2 = Result(
            id="result-2",
            challenge_id="challenge-1",
            engine_id="engine-2",
            task_id="task-1",
            quality_score=0.85
        )
        result3 = Result(
            id="result-3",
            challenge_id="challenge-2",
            engine_id="engine-1",
            task_id="task-2",
            quality_score=0.88
        )
        
        collection.append(result1)
        collection.append(result2)
        collection.append(result3)
        
        engine1_results = collection.by_engine("engine-1")
        assert len(engine1_results) == 2
        assert engine1_results[0].id == "result-1"
        assert engine1_results[1].id == "result-3"
    
    def test_result_collection_by_challenge(self):
        """Test filtering results by challenge."""
        collection = ResultCollection()
        
        result1 = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92
        )
        result2 = Result(
            id="result-2",
            challenge_id="challenge-1",
            engine_id="engine-2",
            task_id="task-1",
            quality_score=0.85
        )
        result3 = Result(
            id="result-3",
            challenge_id="challenge-2",
            engine_id="engine-1",
            task_id="task-2",
            quality_score=0.88
        )
        
        collection.append(result1)
        collection.append(result2)
        collection.append(result3)
        
        challenge1_results = collection.by_challenge("challenge-1")
        assert len(challenge1_results) == 2
        assert challenge1_results[0].id == "result-1"
        assert challenge1_results[1].id == "result-2"


class TestCSVExport:
    """Unit tests for CSV export functionality."""
    
    def test_csv_columns_count_matches_row_fields(self):
        """Test that CSV columns match row fields."""
        collection = ResultCollection()
        
        result = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            input="Test input",
            output="Test output",
            quality_score=0.92,
            safety_score=0.98,
            accuracy_score=0.89
        )
        collection.append(result)
        
        csv_lines = collection.to_csv()
        assert len(csv_lines) > 1  # Header + data
        
        # Count columns in header
        header = csv_lines[0].strip().split(",")
        assert len(header) > 10  # Should have many columns
    
    def test_csv_export_empty_collection(self):
        """Test CSV export of empty collection."""
        collection = ResultCollection()
        csv_lines = collection.to_csv()
        assert len(csv_lines) == 1  # Just header
        assert "id" in csv_lines[0].strip()
