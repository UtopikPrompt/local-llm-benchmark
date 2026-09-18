# Local LLM Benchmark

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Architecture Overview](#architecture-overview)
5. [Running Benchmarks](#running-benchmarks)
6. [Configuration](#configuration)
7. [Results & Visualization](#results--visualization)
8. [Performance Tuning](#performance-tuning)
9. [API Reference](#api-reference)
10. [Development](#development)
11. [Troubleshooting](#troubleshooting)
12. [Contributing](#contributing)

---

## Introduction

Local LLM Benchmark is a comprehensive benchmarking tool designed to compare the performance of local Large Language Model (LLM) engines including Ollama and LM Studio. It provides:

- **Fast inference benchmarking** using HTTP client configuration
- **Multi-threaded request handling** with connection pooling
- **Browser-based visualization** with real-time metrics
- **Prometheus metrics** for monitoring and alerting
- **Configurable timeout and retry logic**

### Key Features

| Feature | Description |
|---------|-------------|
| 🚀 **Speed Testing** | Measure inference latency with configurable concurrency |
| 📊 **Visualization** | Interactive charts and tables in browser UI |
| 🔧 **Configuration** | YAML-based config for engine settings |
| 📈 **Metrics** | Prometheus metrics for external monitoring |
| 🔄 **Retry Logic** | Automatic retry with exponential backoff |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or poetry (recommended)
- Node.js 18+ (for frontend build)
- npm (for frontend dependencies)

### Quick Install

```bash
# Using poetry (recommended)
poetry install

# Using pip
pip install -e ".[dev,e2e]"
```

### Install Frontend Dependencies

```bash
npm install
```

---

## Quick Start

### 1. Configure Engines

Create a `config.yaml` file in the project root:

```yaml
engines:
  ollama:
    url: "http://localhost:11434"
    models:
      - llama3.2:1b
      - mistral:7b
  lmstudio:
    url: "http://localhost:1234"
    models:
      - llama3.2-3b-instruct-q4_0

# HTTP Client Configuration
http_client:
  max_connections: 100
  keepalive_connections: 50
  timeout: 60.0
  max_retries: 3
  retry_backoff: "exponential"
```

### 2. Start the Server

```bash
# Start the benchmark server
python -m local_llm_benchmark

# Or using poetry
poetry run python -m local_llm_benchmark

# The server will start on http://127.0.0.1:8000
```

### 3. Open the Dashboard

Navigate to `http://127.0.0.1:8000` in your browser to see the benchmark dashboard.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Local LLM Benchmark                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐         ┌─────────────────┐               │
│  │   HTTP Client   │         │   Engine APIs   │               │
│  │  (httpx/uvicorn)│         │ (Ollama/LMStudio)│              │
│  └────────┬────────┘         └────────┬────────┘               │
│           │                            │                        │
│           ▼                            ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Runner Module                           │   │
│  │  - Benchmark orchestration                              │   │
│  │  - Request scheduling                                   │   │
│  │  - Timeout & retry logic                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   API Layer                              │   │
│  │  - FastAPI endpoints                                   │   │
│  │  - Request validation                                 │   │
│  │  - Response caching                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Frontend Dashboard                      │   │
│  │  - React-like UI (ES modules)                          │   │
│  │  - Chart.js visualizations                             │   │
│  │  - Real-time updates                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | Description |
|--------|-------------|
| `runner.py` | Orchestrates benchmark execution and manages concurrent requests |
| `engines/` | Engine-specific implementations (base, openai_compat) |
| `api/` | FastAPI endpoints for benchmark control |
| `app/ui/` | Frontend dashboard components |
| `cache.py` | Caching layer for repeated benchmarks |
| `metrics.py` | Prometheus metrics collection |

---

## Running Benchmarks

### Via API

```bash
# Start a benchmark
curl -X POST http://127.0.0.1:8000/benchmarks \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "ollama",
    "model": "llama3.2:1b",
    "prompt": "Explain quantum computing in simple terms.",
    "max_tokens": 256,
    "temperature": 0.7
  }'

# List all benchmarks
curl http://127.0.0.1:8000/benchmarks

# Get benchmark details
curl http://127.0.0.1:8000/benchmarks/123
```

### Via Dashboard

1. Open `http://127.0.0.1:8000`
2. Select engine and model
3. Enter prompt and configure parameters
4. Click "Run Benchmark"
5. View results in real-time

---

## Configuration

### config.yaml

```yaml
engines:
  # Engine-specific configurations
  ollama:
    url: "http://localhost:11434"
    models:
      - "llama3.2:1b"
      - "mistral:7b"
  lmstudio:
    url: "http://localhost:1234"
    models:
      - "llama3.2-3b-instruct-q4_0"

# HTTP Client Configuration
http_client:
  max_connections: 100
  keepalive_connections: 50
  timeout: 60.0
  max_retries: 3
  retry_backoff: "exponential"
```

### Prometheus Metrics

```yaml
metrics:
  enabled: true
  port: 8001
  endpoints:
    inference_latency: "inference_latency_seconds"
    tokens_per_second: "tokens_per_second"
    throughput: "throughput_requests_per_second"
```

---

## Results & Visualization

### Metrics Collected

| Metric | Description | Unit |
|--------|-------------|------|
| `inference_latency` | Time to generate full response | seconds |
| `tokens_per_second` | Token generation speed | tokens/s |
| `throughput` | Requests completed per second | req/s |
| `error_rate` | Failed requests percentage | percentage |
| `memory_usage` | Memory consumption | MB |

### Visualization Components

The dashboard provides:

- **Latency Chart**: Response time distribution
- **Throughput Graph**: Requests per second over time
- **Token Speed**: Tokens generated per second
- **Comparison Table**: Side-by-side engine comparison
- **Error Timeline**: Error occurrences over time

---

## Performance Tuning

### Connection Pooling

```yaml
http_client:
  # Increase for high-concurrency scenarios
  max_connections: 200
  keepalive_connections: 100
  
  # Adjust based on network latency
  timeout: 120.0
  
  # Retry configuration
  max_retries: 5
  retry_backoff: "exponential"
```

### Worker Pool Configuration

```python
from local_llm_benchmark.runner import BenchmarkRunner

# Configure worker pool
runner = BenchmarkRunner(
    max_workers=50,  # Number of concurrent requests
    queue_timeout=30.0  # Seconds to wait for work
)
```

### Caching Strategy

```python
from local_llm_benchmark.cache import BenchmarkCache

# LRU cache with TTL
cache = BenchmarkCache(
    max_size=1000,  # Maximum cached entries
    ttl=3600  # Time to live in seconds
)
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/benchmarks` | Create a new benchmark |
| `GET` | `/benchmarks` | List all benchmarks |
| `GET` | `/benchmarks/{id}` | Get benchmark details |
| `DELETE` | `/benchmarks/{id}` | Delete a benchmark |
| `POST` | `/metrics/collect` | Collect metrics |
| `GET` | `/health` | Health check |
| `GET` | `/prometheus` | Prometheus metrics |

### Request/Response Schemas

```python
from pydantic import BaseModel
from typing import Optional

class CreateBenchmark(BaseModel):
    engine: str
    model: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    n: int = 1
    stream: bool = False

class BenchmarkResult(BaseModel):
    id: str
    engine: str
    model: str
    status: str
    latency: float
    tokens_per_second: float
    prompt: str
    created_at: str
```

---

## Development

### Project Structure

```
local-llm-benchmark/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── app/              # Web application
│   ├── local_llm_benchmark/
│   │   ├── runner.py     # Benchmark orchestration
│   │   ├── engines/      # Engine implementations
│   │   ├── cache.py      # Caching layer
│   │   ├── metrics.py    # Prometheus metrics
│   │   └── utils/        # Utility functions
│   └── ui/               # Frontend components
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── config.yaml          # Configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=local_llm_benchmark --cov-report=html

# Run frontend tests
npm test

# Run e2e tests
playwright test
```

---

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```bash
# Check if engine is running
# Ollama: curl http://localhost:11434/api/tags
# LM Studio: Check running processes
```

#### 2. Timeout Errors

```yaml
# Increase timeout
http_client:
  timeout: 120.0
```

#### 3. Memory Issues

```python
# Reduce context window
benchmark:
  context_window: 2048
```

### Debug Mode

```bash
# Enable debug logging
DEBUG=1 python -m local_llm_benchmark
```

---

## Contributing

### Code Style

- Follow PEP 8 for Python
- Use type hints where possible
- Write comprehensive docstrings
- Include tests for new features

### Running Linters

```bash
# Run ruff
ruff check src/

# Run mypy
mypy src/

# Run formatter
ruff format src/
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Run full test suite
5. Submit pull request
6. Address feedback

---

## License

[Add license information here]

---

*Last updated: $(date +%Y-%m-%d)*
