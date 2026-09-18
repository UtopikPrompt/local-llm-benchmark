"""Unit tests for report.py - report generation functionality."""

import pytest
from local_llm_benchmark.report import generate_report, _generate_jsonl_report, _write_jsonl, _write_csv
from local_llm_benchmark.runner import BenchmarkResult


class TestGenerateReport:
    """Test report generation functionality."""

    def test_generate_report_creates_files(self, tmp_path):
        """Test that generate_report creates both JSONL and CSV files."""
        results = [
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-001",
                ttft_s=0.5,
                tok_per_s=50.0,
                quality_passed=True,
            ),
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-002",
                ttft_s=0.3,
                tok_per_s=60.0,
                quality_passed=True,
            ),
            BenchmarkResult(
                engine="openai",
                model="gpt-4o",
                task_id="task-001",
                ttft_s=1.0,
                tok_per_s=100.0,
                quality_passed=True,
            ),
        ]

        report_path = tmp_path / "benchmark_report.jsonl"
        csv_path = tmp_path / "benchmark_report.csv"

        generate_report(results, report_path, csv_path)

        assert report_path.exists()
        assert csv_path.exists()

    def test_generate_report_with_empty_results(self, tmp_path):
        """Test that generate_report handles empty results gracefully."""
        results = []

        report_path = tmp_path / "benchmark_report.jsonl"
        csv_path = tmp_path / "benchmark_report.csv"

        generate_report(results, report_path, csv_path)

        assert report_path.exists()
        assert csv_path.exists()

        # CSV should be empty or minimal
        with open(csv_path, "r") as f:
            lines = f.readlines()
            assert len(lines) >= 1  # At least header row

    def test_generate_report_with_multiple_engines(self, tmp_path):
        """Test report generation with multiple engines."""
        results = [
            BenchmarkResult(engine="ollama", model="llama3", task_id="t1", ttft_s=0.5, tok_per_s=50.0, quality_passed=True),
            BenchmarkResult(engine="ollama", model="mistral", task_id="t1", ttft_s=0.4, tok_per_s=55.0, quality_passed=True),
            BenchmarkResult(engine="openai", model="gpt-4o", task_id="t1", ttft_s=1.0, tok_per_s=100.0, quality_passed=True),
            BenchmarkResult(engine="openai", model="gpt-4o", task_id="t2", ttft_s=0.8, tok_per_s=95.0, quality_passed=True),
        ]

        report_path = tmp_path / "benchmark_report.jsonl"
        csv_path = tmp_path / "benchmark_report.csv"

        generate_report(results, report_path, csv_path)

        # Verify JSONL contains all results
        with open(report_path, "r") as f:
            content = f.read()
            assert "ollama" in content
            assert "mistral" in content
            assert "gpt-4o" in content

        # Verify CSV contains all results
        with open(csv_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == len(results) + 1  # Header + 4 results


class TestGenerateJsonlReport:
    """Test JSONL report generation."""

    def test_generate_jsonl_report_structure(self, tmp_path):
        """Test that JSONL report has correct structure."""
        results = [
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-001",
                ttft_s=0.5,
                tok_per_s=50.0,
                iters_per_s=25.0,
                quality_passed=True,
                quality_deterministic=False,
                quality_judge=False,
                quality_note="Good response",
            ),
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-001",
                ttft_s=0.3,
                tok_per_s=60.0,
                iters_per_s=30.0,
                quality_passed=True,
                quality_deterministic=True,
                quality_judge=False,
                quality_note="Excellent response",
            ),
        ]

        report_path = tmp_path / "report.jsonl"
        _generate_jsonl_report(results, report_path)

        with open(report_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == len(results)

            # Verify each line is valid JSON
            for line in lines:
                import json
                data = json.loads(line)
                assert "engine" in data
                assert "model" in data
                assert "task_id" in data
                assert "ttft_s" in data
                assert "tok_per_s" in data
                assert "iters_per_s" in data
                assert "quality_passed" in data
                assert "quality_deterministic" in data
                assert "quality_judge" in data
                assert "quality_note" in data

    def test_generate_jsonl_report_all_fields(self, tmp_path):
        """Test that JSONL report includes all available fields."""
        results = [
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-001",
                ttft_s=0.5,
                tok_per_s=50.0,
                iters_per_s=25.0,
                quality_passed=True,
                quality_deterministic=False,
                quality_judge=False,
                quality_note="Test note",
            )
        ]

        report_path = tmp_path / "report.jsonl"
        _generate_jsonl_report(results, report_path)

        with open(report_path, "r") as f:
            line = f.readline()
            import json
            data = json.loads(line)

            # Verify all fields from BenchmarkResult are present
            expected_fields = [
                "engine",
                "model",
                "task_id",
                "ttft_s",
                "tok_per_s",
                "iters_per_s",
                "quality_passed",
                "quality_deterministic",
                "quality_judge",
                "quality_note",
            ]

            for field in expected_fields:
                assert field in data, f"Field '{field}' not found in report"


class TestWriteJsonl:
    """Test JSONL file writing."""

    def test_write_jsonl_single_entry(self, tmp_path):
        """Test writing a single JSONL entry."""
        records = [
            {
                "engine": "ollama",
                "model": "llama3",
                "task_id": "task-001",
                "ttft_s": 0.5,
                "tok_per_s": 50.0,
                "iters_per_s": 25.0,
                "quality_passed": True,
                "quality_note": "Good",
            }
        ]

        report_path = tmp_path / "report.jsonl"
        _write_jsonl(records, report_path)

        with open(report_path, "r") as f:
            line = f.readline()
            import json
            data = json.loads(line)
            assert data == records[0]

    def test_write_jsonl_multiple_entries(self, tmp_path):
        """Test writing multiple JSONL entries."""
        records = [
            {"engine": "ollama", "model": "llama3", "task_id": "t1", "ttft_s": 0.5, "tok_per_s": 50.0, "quality_passed": True},
            {"engine": "openai", "model": "gpt-4o", "task_id": "t1", "ttft_s": 1.0, "tok_per_s": 100.0, "quality_passed": True},
        ]

        report_path = tmp_path / "report.jsonl"
        _write_jsonl(records, report_path)

        with open(report_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == len(records)

            # Verify each line is valid JSON
            for line in lines:
                import json
                data = json.loads(line)
                assert data in records


class TestWriteCsv:
    """Test CSV file writing."""

    def test_write_csv_header(self, tmp_path):
        """Test that CSV has correct header row."""
        records = [
            {
                "engine": "ollama",
                "model": "llama3",
                "task_id": "task-001",
                "ttft_s": 0.5,
                "tok_per_s": 50.0,
                "iters_per_s": 25.0,
                "quality_passed": True,
                "quality_note": "Good",
            }
        ]

        report_path = tmp_path / "report.csv"
        _write_csv(records, report_path)

        with open(report_path, "r") as f:
            header = f.readline().strip()
            expected_header = "engine,model,task_id,ttft_s,tok_per_s,iters_per_s,quality_passed,quality_note"
            assert header == expected_header

    def test_write_csv_data_rows(self, tmp_path):
        """Test that CSV has correct data rows."""
        records = [
            {
                "engine": "ollama",
                "model": "llama3",
                "task_id": "task-001",
                "ttft_s": 0.5,
                "tok_per_s": 50.0,
                "iters_per_s": 25.0,
                "quality_passed": True,
                "quality_note": "Good",
            },
            {
                "engine": "openai",
                "model": "gpt-4o",
                "task_id": "task-001",
                "ttft_s": 1.0,
                "tok_per_s": 100.0,
                "iters_per_s": 50.0,
                "quality_passed": True,
                "quality_note": "Excellent",
            },
        ]

        report_path = tmp_path / "report.csv"
        _write_csv(records, report_path)

        with open(report_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == len(records) + 1  # Header + 2 data rows

            # Verify data rows
            for i, record in enumerate(records):
                line = lines[i + 1].strip()
                # Parse CSV line
                columns = line.split(",")
                assert columns[0] == record["engine"]
                assert columns[1] == record["model"]
                assert float(columns[3]) == record["ttft_s"]
                assert float(columns[4]) == record["tok_per_s"]
                assert float(columns[5]) == record["iters_per_s"]
                assert columns[6] == str(record["quality_passed"]).lower()
                assert columns[7] == record["quality_note"]

    def test_write_csv_bool_conversion(self, tmp_path):
        """Test boolean conversion in CSV output."""
        records = [
            {
                "engine": "ollama",
                "model": "llama3",
                "task_id": "task-001",
                "ttft_s": 0.5,
                "tok_per_s": 50.0,
                "iters_per_s": 25.0,
                "quality_passed": True,
                "quality_note": "",
            },
            {
                "engine": "ollama",
                "model": "llama3",
                "task_id": "task-002",
                "ttft_s": 0.5,
                "tok_per_s": 50.0,
                "iters_per_s": 25.0,
                "quality_passed": False,
                "quality_note": "",
            },
        ]

        report_path = tmp_path / "report.csv"
        _write_csv(records, report_path)

        with open(report_path, "r") as f:
            lines = f.readlines()
            # First data row should have "True", second should have "False"
            assert "True" in lines[1]
            assert "False" in lines[2]


class TestReportGenerationEdgeCases:
    """Test edge cases in report generation."""

    def test_generate_report_special_characters(self, tmp_path):
        """Test report generation with special characters."""
        results = [
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-001",
                ttft_s=0.5,
                tok_per_s=50.0,
                quality_passed=True,
            ),
            BenchmarkResult(
                engine="ollama",
                model="llama3",
                task_id="task-002",
                ttft_s=0.5,
                tok_per_s=50.0,
                quality_passed=False,
            ),
        ]

        report_path = tmp_path / "benchmark_report.jsonl"
        csv_path = tmp_path / "benchmark_report.csv"

        generate_report(results, report_path, csv_path)

        # Verify files were created successfully
        assert report_path.exists()
        assert csv_path.exists()

    def test_generate_report_large_dataset(self, tmp_path):
        """Test report generation with larger dataset."""
        # Generate 1000 results
        results = [
            BenchmarkResult(
                engine="ollama",
                model=f"llama3-{i % 3}",
                task_id=f"task-{i}",
                ttft_s=float(i * 0.1),
                tok_per_s=float(50 + i),
                quality_passed=i % 3 == 0,
            )
            for i in range(1000)
        ]

        report_path = tmp_path / "benchmark_report.jsonl"
        csv_path = tmp_path / "benchmark_report.csv"

        generate_report(results, report_path, csv_path)

        # Verify files were created
        assert report_path.exists()
        assert csv_path.exists()

        # Verify CSV has correct number of rows
        with open(csv_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1001  # Header + 1000 results
