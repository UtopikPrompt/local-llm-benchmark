"""Application-wide configuration management.

This module provides a centralized configuration system supporting:
- Environment variables for runtime configuration
- Environment-specific defaults via pyproject.toml
- Pydantic dataclasses for type-safe configuration
- Config file persistence and validation
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional
from pydantic import Field, field_validator

from .logger import logger


# ============================================================================
# Configuration Constants (from pyproject.toml)
# ============================================================================

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8080/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# HTTP Client Configuration
HTTP_MAX_CONNECTIONS = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
HTTP_KEEPALIVE_CONNECTIONS = int(os.getenv("HTTP_KEEPALIVE_CONNECTIONS", "50"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "60.0"))
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "3"))
HTTP_RETRY_BACKOFF = os.getenv("HTTP_RETRY_BACKOFF", "exponential")

# Database Configuration
DB_URL = os.getenv("DB_URL", "sqlite:///./benchmark.db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))

# Application Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
DEFAULT_RESULTS_DIR = os.getenv("DEFAULT_RESULTS_DIR", "./results")


# ============================================================================
# Configuration Dataclasses
# ============================================================================

@dataclass
class LLMConfig:
    """LLM client configuration."""
    base_url: str = Field(default=LLM_BASE_URL)
    api_key: Optional[str] = Field(default=None)
    timeout: float = Field(default=LLM_TIMEOUT)
    max_retries: int = Field(default=LLM_MAX_RETRIES)
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        """Ensure base_url ends with /v1 for OpenAPI compatibility."""
        if not value.endswith("/v1"):
            return value + "/v1"
        return value


@dataclass
class HTTPConfig:
    """HTTP client configuration for httpx."""
    max_connections: int = Field(default=HTTP_MAX_CONNECTIONS)
    keepalive_connections: int = Field(default=HTTP_KEEPALIVE_CONNECTIONS)
    timeout: float = Field(default=HTTP_TIMEOUT)
    max_retries: int = Field(default=HTTP_MAX_RETRIES)
    retry_backoff: str = Field(default=HTTP_RETRY_BACKOFF)


@dataclass
class DBConfig:
    """Database configuration."""
    url: str = Field(default=DB_URL)
    pool_size: int = Field(default=DB_POOL_SIZE)
    max_overflow: int = Field(default=DB_MAX_OVERFLOW)


@dataclass
class AppConfig:
    """Application-wide configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    http: HTTPConfig = Field(default_factory=HTTPConfig)
    
    # Other configuration
    cache_ttl: int = Field(default=CACHE_TTL)
    max_concurrent_requests: int = Field(default=MAX_CONCURRENT_REQUESTS)
    default_results_dir: str = Field(default=DEFAULT_RESULTS_DIR)


@dataclass
class CORSConfig:
    """CORS configuration."""
    allow_all_origins: bool = Field(default=False)
    origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])
    allowed_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: list[str] = Field(default_factory=lambda: [
        "Content-Type", 
        "Authorization", 
        "Origin", 
        "Accept", 
        "Accept-Language",
        "Content-Length",
        "Cache-Control",
        "Keep-Alive",
        "Connection"
    ])
    allow_credentials: bool = Field(default=True)
    max_age: int = Field(default=86400)  # 24 hours in seconds


@dataclass
class TokenConfig:
    """JWT token configuration."""
    secret_key: str = Field(default="your-secret-key-change-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_hours: int = Field(default=24)
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Ensure secret key is at least 32 characters."""
        if len(value) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        return value


@dataclass
class Role:
    """User roles with permission levels."""
    name: str = Field()
    description: str = Field(default="")
    permissions: list[str] = Field(default_factory=list)
    
    @property
    def is_admin(self) -> bool:
        """Check if role has admin permissions."""
        return "admin" in self.permissions
    
    @property
    def is_viewer(self) -> bool:
        """Check if role has viewer permissions."""
        return "view" in self.permissions


# Predefined roles
ADMIN_ROLE = Role(name="admin", description="Full system access", permissions=["admin", "view", "create", "update", "delete", "manage_users"])
VIEWER_ROLE = Role(name="viewer", description="Read-only access", permissions=["view"])
BENCHMARKER_ROLE = Role(name="benchmarker", description="Can run benchmarks", permissions=["view", "create", "run_benchmarks"])


# Configuration Loading and Saving
# ============================================================================

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from file or use defaults.
    
    Args:
        config_path: Optional path to a config file. Defaults to 
            the project root config.yaml.
    
    Returns:
        AppConfig instance with loaded or default values.
    
    Raises:
        ConfigError: If the config file cannot be loaded or parsed.
    """
    import yaml
    
    if config_path is None:
        config_path = get_config_path()
    
    logger.info("Loading configuration", extra={"config_path": config_path})
    
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return AppConfig()
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    
    # Merge with defaults
    config = AppConfig()
    if data:
        # Apply nested config
        if "llm" in data:
            if isinstance(data["llm"], dict):
                config.llm = LLMConfig(**data["llm"])
            else:
                config.llm = data["llm"]
        if "db" in data:
            if isinstance(data["db"], dict):
                config.db = DBConfig(**data["db"])
            else:
                config.db = data["db"]
        if "http" in data:
            if isinstance(data["http"], dict):
                config.http = HTTPConfig(**data["http"])
            else:
                config.http = data["http"]
        
        # Apply top-level config
        config.cache_ttl = data.get("cache_ttl", config.cache_ttl)
        config.max_concurrent_requests = data.get(
            "max_concurrent_requests", config.max_concurrent_requests
        )
    
    return config


def save_config(config: AppConfig, path: Optional[str] = None) -> None:
    """Save configuration to file.
    
    Args:
        config: AppConfig instance to save
        path: Optional output path. Defaults to project root config.yaml.
    """
    import yaml
    
    if path is None:
        path = get_config_path()
    
    logger.info("Saving configuration", extra={"config_path": path})
    
    # Prepare data for YAML serialization
    data = {
        "llm": {
            "base_url": config.llm.base_url,
            "api_key": config.llm.api_key,
            "timeout": config.llm.timeout,
            "max_retries": config.llm.max_retries,
        },
        "db": {
            "url": config.db.url,
            "pool_size": config.db.pool_size,
            "max_overflow": config.db.max_overflow,
        },
        "http": {
            "max_connections": config.http.max_connections,
            "keepalive_connections": config.http.keepalive_connections,
            "timeout": config.http.timeout,
            "max_retries": config.http.max_retries,
            "retry_backoff": config.http.retry_backoff,
        },
        "cache_ttl": config.cache_ttl,
        "max_concurrent_requests": config.max_concurrent_requests,
    }
    
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_config_path() -> str:
    """Get the default configuration file path."""
    import os
    logger.debug("Determining config path")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


# ============================================================================
# Backward Compatibility: Config is an alias for AppConfig
# ============================================================================

Config = AppConfig
