# Developer Guide

---

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Architecture](#project-architecture)
3. [Code Style & Conventions](#code-style--conventions)
4. [Testing Guidelines](#testing-guidelines)
5. [CI/CD Workflow](#cicd-workflow)
6. [Debugging Tips](#debugging-tips)
7. [Performance Optimization](#performance-optimization)
8. [Documentation Standards](#documentation-standards)
9. [Architecture Decision Records](#architecture-decision-records)
10. [Common Tasks](#common-tasks)

---

## Development Environment Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# pip/poetry
pip --version
poetry --version  # Recommended

# Node.js
node --version
npm --version

# Git
git --version
```

### Installation

```bash
# Clone repository
git clone <repo-url>
cd local-llm-benchmark

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
poetry install

# Install frontend dependencies
npm install

# Generate type stubs (if needed)
python -m mypy src/ --no-error-summary
```

### VS Code Setup

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [80, 100],
    "files.autoSave": "focuschange",
    "files.eol": "\n"
}
```

Install recommended extensions:
- Python (Microsoft)
- Pylance
- Ruff
- GitLens
- Live Server

---

## Project Architecture

### Module Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL LLM BENCHMARK                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   API Layer  │  │   Runner     │  │    UI Layer  │      │
│  │  (FastAPI)   │  │  (Orchestration)│  │  (ES Modules)│     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                            │                                │
│                             ▼                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Core Modules                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │  Engines │  │  Cache   │  │  Metrics │           │   │
│  │  │ (Base)   │  │  Layer   │  │  (Prom)  │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```bash
local-llm-benchmark/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── controller.py    # Request handlers
│   │   └── services.py      # Business logic
│   ├── app/
│   │   ├── __init__.py
│   │   ├── dashboard.html   # Main page
│   │   └── ui/
│   │       ├── app.js       # Application state
│   │       ├── main.js      # Entry point
│   │       ├── models.js    # Data models
│   │       ├── utils.js     # Utility functions
│   │       ├── views.js     # UI components
│   │       ├── state.js     # State management
│   │       ├── dom.js       # DOM helpers
│   │       ├── challenges.js # Challenge logic
│   │       └── results.js   # Results display
│   ├── local_llm_benchmark/
│   │   ├── __init__.py
│   │   ├── runner.py        # Benchmark orchestration
│   │   ├── config.py        # Configuration loading
│   │   ├── errors.py        # Custom exceptions
│   │   ├── errors_clean.py  # Cleaned errors
│   │   ├── errors_fixed.py  # Fixed errors
│   │   ├── build.py         # Build utilities
│   │   ├── cache.py         # Caching
│   │   ├── di.py            # Dependency injection
│   │   ├── logger.py        # Logging setup
│   │   ├── middleware.py    # Request middleware
│   │   ├── rate_limiter.py  # Rate limiting
│   │   ├── report.py        # Report generation
│   │   ├── response.py      # Response helpers
│   │   ├── services.py      # Core services
│   │   ├── alerts.py        # Alerting
│   │   ├── metrics.py       # Prometheus metrics
│   │   ├── results.py       # Results handling
│   │   └── utils/           # Utils package
│   │       ├── __init__.py
│   │       ├── http_client.py   # HTTP client config
│   │       ├── engine_manager.py# Engine management
│   │       ├── timeout.py       # Timeout utilities
│   │       └── retry.py         # Retry logic
│   └── engines/
│       ├── __init__.py
│       ├── base.py           # Base engine class
│       ├── engine.py         # Engine interface
│       └── openai_compat.py  # OpenAI-compatible adapter
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_runner.py        # Runner tests
│   ├── test_engines.py       # Engine tests
│   ├── test_services.py      # Service tests
│   ├── test_cache.py         # Cache tests
│   ├── test_config.py        # Config tests
│   └── test_results.py       # Results tests
├── e2e/
│   └── tests/
│       └── integration/
│           ├── test_api.py
│           └── test_db.py
├── ui/
│   ├── test_challenges.js
│   ├── test_dom.js
│   ├── test_models.js
│   ├── test_results.js
│   ├── test_state.js
│   └── test_utils.js
├── docs/
│   ├── user_guide.md         # User documentation
│   ├── developer_guide.md    # This file
│   └── api/
│       ├── index.rst
│       ├── overview.rst
│       ├── modules.rst
│       ├── engine.rst
│       ├── runner.rst
│       └── ui.rst
├── adr/
│   ├── 0000-adr-template.md
│   ├── 0001-project-purpose.md
│   └── ... (see docs/)
├── config.yaml               # Default configuration
├── pyproject.toml            # Python project config
├── package.json              # Node.js config
├── vitest.config.js          # Frontend test config
├── esbuild.config.js         # Frontend build config
└── README.md                 # Project overview
```

---

## Code Style & Conventions

### Python Style

#### PEP 8 Compliance

```python
# GOOD
import os
import httpx
from typing import Optional, List

class BenchmarkRunner:
    """Benchmark runner class."""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._clients: List[httpx.Client] = []
    
    def run_benchmark(self, config: dict) -> dict:
        """Run a benchmark using the given configuration."""
        pass
```

#### Type Hints

```python
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    engine: str
    model: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    timeout: Optional[float] = None
```

#### Docstrings

```python
def calculate_latency(response: httpx.Response) -> float:
    """Calculate the total latency for a response.
    
    Args:
        response: The HTTP response object.
        
    Returns:
        Total latency in seconds, including request time and response time.
        
    Raises:
        ValueError: If response is None or has no elapsed time.
        
    Examples:
        >>> response = httpx.get("http://example.com")
        >>> latency = calculate_latency(response)
        >>> latency  # 0.045 seconds
        0.045
    """
    if response is None:
        raise ValueError("Response cannot be None")
    return response.elapsed.total_seconds()
```

### JavaScript/TypeScript Style

#### ES Module Conventions

```javascript
// src/app/ui/models.js
import { createEvent, createSignal } from './state.js';

export const BenchmarkResult = createSignal({
  id: '',
  engine: '',
  latency: 0,
  tokensPerSecond: 0
});

export function createBenchmarkResult(
  id: string,
  engine: string,
  latency: number,
  tokensPerSecond: number
) {
  return {
    id,
    engine,
    latency,
    tokensPerSecond
  };
}
```

#### Utility Functions

```javascript
// src/app/ui/utils.js
import { createEvent } from './state.js';

export const formatLatency = (ms: number) => {
  if (ms < 1) return `${ms * 1000}ms`;
  if (ms < 1000) return `${ms.toFixed(3)}ms`;
  return `${(ms / 1000).toFixed(3)}s`;
};

export const formatTokens = (tokens: number) => {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(2)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(2)}K`;
  return tokens.toString();
};
```

### Linting Rules

```bash
# Run ruff
ruff check src/ --output-format=concise

# Run mypy
mypy src/

# Auto-fix issues
ruff check --fix src/
ruff format src/
```

---

## Testing Guidelines

### Test Structure

```python
# tests/test_runner.py
import pytest
from local_llm_benchmark.runner import BenchmarkRunner
from local_llm_benchmark.config import Config


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""
    
    def test_init_creates_runner(self):
        """Test that runner initializes correctly."""
        runner = BenchmarkRunner(max_workers=10)
        assert runner.max_workers == 10
        assert len(runner._clients) == 0
    
    def test_run_benchmark_returns_result(self, mock_client):
        """Test that running a benchmark returns a result."""
        runner = BenchmarkRunner(max_workers=5)
        result = runner.run_benchmark({
            'engine': 'ollama',
            'model': 'llama3.2:1b'
        })
        
        assert result is not None
        assert 'latency' in result
        assert 'tokens_per_second' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_client):
        """Test concurrent request handling."""
        runner = BenchmarkRunner(max_workers=100)
        
        async def benchmark_request(engine_config):
            return await runner._request(engine_config)
        
        # Run 50 concurrent requests
        tasks = [benchmark_request({}) for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 50


@pytest.fixture
def mock_client():
    """Mock httpx client for testing."""
    with patch('httpx.Client') as mock:
        mock.return_value.request.return_value = MagicMock()
        yield mock
```

### Test Coverage Requirements

| Module | Minimum Coverage | 
|--------|------------------|
| `runner.py` | 90% |
| `engines/` | 85% |
| `api/` | 80% |
| `app/ui/` | 75% |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=local_llm_benchmark --cov-report=term-missing

# Run specific test file
pytest tests/test_runner.py

# Run async tests
pytest -k asyncio

# Run frontend tests
npm test

# Run e2e tests
playwright test

# Generate coverage report
pytest --cov=local_llm_benchmark --cov-report=html
open coverage_html_report.html
```

---

## CI/CD Workflow

### GitHub Actions

`.github/workflows/ci.yml`

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Linting
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff
      - run: ruff check src/ tests/
  
  # Type Checking
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install mypy
      - run: mypy src/
  
  # Unit Tests
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=local_llm_benchmark --cov-report=xml
  
  # Code Coverage
  coverage:
    runs-on: ubuntu-latest
    needs: [test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=local_llm_benchmark --cov-report=term-missing
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Debugging Tips

### Debugging Python Code

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for interactive debugging
import pdb
pdb.set_trace()

# Use ipdb for better debugger
import ipdb; ipdb.set_trace()

# Use pytest debuggers
pytest --pdb
pytest -xvs
```

### Debugging JavaScript

```javascript
// Enable console logging
console.log('Benchmark started:', config);

// Use browser debugger
// Open DevTools (F12) -> Console

// Use React DevTools
npm install --save-dev @testing-library/react-devtools
npm run dev -- --port 3001
```

### Common Debug Scenarios

| Issue | Debug Command | Tool |
|-------|---------------|------|
| Network request failing | `curl -v http://localhost:8000` | curl |
| Thread deadlock | `threading.enumerate()` | Python |
| Memory leak | `tracemalloc.start()` | Python |
| Frontend state issue | Check DevTools Console | Browser |
| API response error | Check response body | Postman |

---

## Performance Optimization

### Connection Pooling

```python
# Reuse connections
httpx.Client(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=50
    ),
    timeout=httpx.Timeout(60.0)
)
```

### Worker Pool Configuration

```python
# Optimize worker count
from local_llm_benchmark.runner import BenchmarkRunner

runner = BenchmarkRunner(
    max_workers=min(os.cpu_count() * 2, 100),  # CPU-bound
    queue_timeout=30.0  # Don't wait forever
)
```

### Caching Strategy

```python
# LRU cache with TTL
from functools import lru_cache
from cachetools import TTLCache

@lru_cache(maxsize=1000)
def cached_benchmark(config: tuple) -> dict:
    return run_benchmark(config)

# Manual cache
cache = TTLCache(maxsize=1000, ttl=3600)
```

### Benchmark Configuration

```yaml
# Optimize for fair comparison
http_client:
  max_connections: 100
  keepalive_connections: 50
  timeout: 60.0
  max_retries: 3
  retry_backoff: "exponential"

runner:
  max_workers: 100
  warmup_requests: 10
  warmup_duration: 5.0
```

---

## Documentation Standards

### Docstring Format

```python
def benchmark_engine(
    engine: str,
    model: str,
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.7
) -> dict:
    """Benchmark an LLM engine.
    
    Runs a benchmark against the specified engine and model.
    
    Args:
        engine: Engine name (e.g., 'ollama', 'lmstudio')
        model: Model identifier
        prompt: Prompt text to benchmark
        max_tokens: Maximum tokens to generate (default: 256)
        temperature: Sampling temperature (default: 0.7)
        
    Returns:
        Dictionary with benchmark results including latency
        and tokens per second.
        
    Raises:
        EngineError: If the engine is unavailable.
        TimeoutError: If the request times out.
        
    Examples:
        >>> result = benchmark_engine('ollama', 'llama3.2:1b', 'Hello')
        >>> result['latency']  # 0.5 seconds
        0.5
        
        >>> result['tokens_per_second']  # 500 tokens/s
        500.0
    """
```

### API Documentation

```rst
.. automodule:: local_llm_benchmark.runner
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: local_llm_benchmark.runner.BenchmarkRunner
   :members:
   :special-members:
   __init__, run_benchmark, _request

.. autofunction:: local_llm_benchmark.runner.calculate_latency
```

---

## Architecture Decision Records

### ADR Format

```
adr-0001-project-purpose.md

## Title
Project purpose and goals

## Context
Why we are making this decision.

## Decision
What we are deciding.

## Consequences
Pros and cons of the decision.

## Status
- draft: Under consideration
- deprecated: No longer relevant
- superseded: Superseded by another ADR
- implemented: Actively implemented
- abandoned: No longer pursued

## References
- [Related issues](#)
- [Linked ADRs](#)
```

---

## Common Tasks

### Adding a New Engine

```python
# 1. Create engine module
src/engines/my_engine.py

# 2. Implement base class
class MyEngine(BaseEngine):
    """My custom engine implementation."""
    
    def __init__(self, config: dict):
        self.config = config
        self._client = None
    
    async def send(self, prompt: str, **kwargs) -> dict:
        """Send prompt and receive response."""
        pass

# 3. Register engine
src/engines/__init__.py
from .my_engine import MyEngine

# 4. Add tests
tests/test_my_engine.py
```

### Adding a New Endpoint

```python
# 1. Add to API controller
src/api/controller.py

@app.post("/benchmarks")
async def create_benchmark(
    benchmark: CreateBenchmark = Body(...)
) -> CreateBenchmarkResponse:
    """Create a new benchmark."""
    return await create_benchmark(benchmark)

# 2. Add Pydantic models
src/api/schemas/benchmark.py

class CreateBenchmark(BaseModel):
    engine: str
    model: str
    prompt: str
    # ... fields
```

### Writing a New Test

```python
# tests/test_new_feature.py
import pytest
from local_llm_benchmark.module import MyClass


class TestMyClass:
    def test_feature(self):
        """Test the new feature."""
        obj = MyClass(config={})
        result = obj.method()
        assert result == expected
```

---

*Last updated: 2024*
