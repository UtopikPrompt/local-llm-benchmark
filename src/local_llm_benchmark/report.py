"""Report generation utilities."""

import json
import csv
from datetime import datetime
from typing import Any

from .logger import BenchmarkLogger, logger


def generate_report(results: dict, output_path: str, format: str) -> str:
    """Generate a report from benchmark results.

    Args:
        results: Benchmark results dictionary
        output_path: Path to save the report
        format: Output format (jsonl or csv)

    Returns:
        Path to the generated report
    """
    logger = BenchmarkLogger("report")
    logger.info("Generating report", extra={
        "output_path": output_path,
        "format": format,
    })

    if format == "jsonl":
        report = _generate_jsonl_report(results)
        _write_jsonl(report, output_path)
    elif format == "csv":
        report = _generate_csv_report(results)
        _write_csv(report, output_path)
    else:
        logger.error(f"Unsupported format: {format}")
        raise ValueError(f"Unsupported format: {format}")

    logger.info("Report generated successfully", extra={
        "path": output_path,
    })

    return output_path


def _generate_jsonl_report(results: dict) -> list[dict]:
    """Generate a JSONL report from benchmark results."""
    report = []

    # Header
    header = {
        "timestamp": datetime.now().isoformat(),
        "report_type": "benchmark_results",
        "benchmark_name": results.get("name", "unknown"),
    }
    report.append(header)

    # Metrics summary
    metrics = results.get("metrics", {})
    summary = {
        "name": results.get("name", "unknown"),
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    report.append(summary)

    # Individual results
    results_data = results.get("results", [])
    for idx, result in enumerate(results_data):
        result_entry = {
            "index": idx,
            "success": result.get("success", False),
            "response_time": result.get("response_time", 0),
            "tokens_generated": result.get("tokens_generated", 0),
            "completion_time": result.get("completion_time", 0),
            "total_time": result.get("total_time", 0),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "raw_output": result.get("output", ""),
        }
        report.append(result_entry)

    return report


def _generate_csv_report(results: dict) -> list[dict]:
    """Generate a CSV report from benchmark results."""
    report = []

    # Header
    header = {
        "timestamp": datetime.now().isoformat(),
        "report_type": "benchmark_results",
        "benchmark_name": results.get("name", "unknown"),
    }
    report.append(header)

    # Metrics summary
    metrics = results.get("metrics", {})
    summary = {
        "name": results.get("name", "unknown"),
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    report.append(summary)

    # Individual results
    results_data = results.get("results", [])
    for idx, result in enumerate(results_data):
        result_entry = {
            "index": idx,
            "success": result.get("success", False),
            "response_time": result.get("response_time", 0),
            "tokens_generated": result.get("tokens_generated", 0),
            "completion_time": result.get("completion_time", 0),
            "total_time": result.get("total_time", 0),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "raw_output": result.get("output", ""),
        }
        report.append(result_entry)

    return report


def _write_jsonl(data: list[dict], path: str) -> None:
    """Write data to a JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, default=str, ensure_ascii=False) + "\n")


def _write_csv(data: list[dict], path: str) -> None:
    """Write data to a CSV file."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
