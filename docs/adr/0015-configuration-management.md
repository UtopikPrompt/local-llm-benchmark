# Architectural Decision Record: Configuration Management

* **Title:** Configuration Management
* **Status:** `.pill` **Accepted**
* **Date:** 2026-09-18
* **Authors:** Local LLM Benchmark Team

---

## 📋 Problem Statement / Motivation

The `local-llm-benchmark` codebase currently relies on hardcoded configuration values scattered across modules. This creates several operational and maintainability problems:

- **Deployment Friction**: Changing a connection URL or timeout requires code edits and a redeploy
- **Environment Parity**: No formal mechanism to switch between development, test, and production settings
- **Validation Gaps**: Raw environment variable reads have no schema enforcement, silently producing `None` or wrong types
- **Discoverability**: Developers must hunt through source files to understand what is configurable

### Key Observations

1. The application has at least three distinct configuration domains: LLM client settings, database connection settings, and application-level settings (cache TTL, concurrency limits)
2. `pyproject.toml` already manages project metadata; Hatch's `env-set` feature can canonically declare development defaults
3. A typed configuration layer eliminates the need for ad-hoc `os.getenv()` calls spread across modules

This decision formalizes two complementary strategies:

1. **Environment-Based Configuration** — declare defaults and overrides in `pyproject.toml` using `hatch.envs`
2. **Pydantic Config Classes** — enforce schema validation and provide IDE-visible documentation for all settings

---

## ✨ Decision

We will implement a two-layer configuration management strategy.

### 1.1 Environment-Based Configuration via `pyproject.toml`

Declare development environment defaults in `pyproject.toml` so they are version-controlled and reproducible:

```toml
# pyproject.toml
[tool.hatch.envs.local]
python = "3.12"

[tool.hatch.envs.local.plugins]
httpx = "*"

[tool.hatch.envs.local.env-set]
LLM_BASE_URL = "http://localhost:8080/v1"
API_KEY = "test-key"
DB_URL = "sqlite:///./dev.db"
```

### 1.2 Typed Config Classes via Pydantic Dataclasses

Group configuration into validated, typed dataclasses for each domain:

```python
# src/local_llm_benchmark/config.py

from dataclasses import dataclass, field
from typing import Optional
from pydantic import Field


@dataclass
class LLMConfig:
    """LLM client configuration."""
    base_url: str = Field(default="http://localhost:8080/v1")
    api_key: Optional[str] = Field(default=None)
    timeout: float = Field(default=120.0)
    max_retries: int = Field(default=3)


@dataclass
class DBConfig:
    """Database configuration."""
    url: str = Field(default="sqlite:///./benchmark.db")
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)


@dataclass
class AppConfig:
    """Application-wide configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    db: DBConfig = Field(default_factory=DBConfig)

    # Other configuration
    cache_ttl: int = Field(default=3600)
    max_concurrent_requests: int = Field(default=100)
```

---

## 💡 Decision Rationale

| Factor | Rationale |
|--------|-----------|
| **Correctness** | Pydantic validates types and raises early if a required value is missing or malformed |
| **Discoverability** | A single `config.py` file documents every configurable parameter in one place |
| **Portability** | Environment variable overrides allow the same codebase to run in dev, CI, and production without code changes |
| **Minimal Overhead** | Pydantic dataclasses add negligible startup cost while significantly improving reliability |

### Trade-offs Accepted

- **Additional Dependency**: Pydantic is already used for API schemas; this extends its scope to config, adding minimal surface area
- **Migration Effort**: Existing hardcoded values must be replaced with config lookups
- **Learning Curve**: Contributors must understand the config hierarchy to add new settings correctly

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Raw `os.getenv()` Calls (Status Quo)

*Pros:* Zero abstraction overhead; immediately readable

*Cons:*
- No validation; `None` propagates silently to runtime errors
- Settings are scattered across modules with no single source of truth
- Impossible to list all configurable parameters without grepping the entire codebase

*Rationale for Rejection:* Already causing latent bugs; a typed layer is warranted.

### Alternative B: `python-dotenv` with a flat `.env` File

*Pros:*
- Simple and widely understood convention
- Compatible with Docker Compose and most CI platforms

*Cons:*
- No schema validation; values are always strings
- `.env` files can be accidentally committed, leaking secrets
- No grouping or namespacing for related settings

*Rationale for Rejection:* Pydantic dataclasses provide validation and grouping that `.env` alone cannot; `pyproject.toml` env-set achieves the same portability for development defaults.

### Alternative C: YAML/TOML Configuration File (Read at Runtime)

*Pros:*
- Rich data types (arrays, maps) without environment variable serialization
- Easy to diff in version control

*Cons:*
- Requires a file path convention and a parser
- Secrets should not live in version-controlled YAML
- Overriding individual values in CI requires file manipulation

*Rationale for Rejection:* Environment variables are the standard mechanism for container deployments; a file-based config would be a secondary channel requiring additional tooling.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* [**Type Safety**]: Invalid configuration values are caught at startup rather than at the call site, producing clear error messages
* [**Single Source of Truth**]: All configurable parameters documented in `config.py`; no more scattered `os.getenv()` calls
* [**Environment Portability**]: The same codebase runs in dev, CI, and production by setting environment variables
* [**Testability**]: Config objects can be instantiated with overrides in tests without patching `os.environ`

### 🔴 Negative Impacts / Trade-offs

* [**Migration Cost**]: Existing hardcoded values require a one-time refactor to route through the config layer
* [**Startup Validation**]: Applications will fail to start if required environment variables are absent (intentional but may surprise newcomers)
* [**Secret Handling**]: `API_KEY` in `pyproject.toml` env-set is for development only; production secrets must be injected at deploy time, not stored in the repo

---

## 🔗 Related ADRs

* [ADR 0010 - Async HTTP Client Configuration](./0010-http-client-configuration.md) — `LLMConfig` subsumes the timeout and pool settings formalized in this ADR
* [ADR 0007 - Module Loading and Dependency Graph Management](./0007-module-discovery-pattern.md) — Engine discovery depends on configuration values that should flow through `AppConfig`
