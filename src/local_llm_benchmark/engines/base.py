"""LLM engine base class with optimized httpx.AsyncClient configuration."""

import asyncio
import httpx
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from ..logger import BenchmarkLogger, logger
from ..schemas.engine import EngineConfig, EngineResult
from ..schemas.response import LLMResponse


class BaseLLMEngine:
    """Base LLM engine with optimized HTTP client configuration.
    
    This class provides:
    - Connection pooling for high-concurrency scenarios
    - Connection reuse via keep-alive settings
    - Persistent httpx.AsyncClient for KV-cache reuse
    - Timeout configuration for request reliability
    """
    
    # Connection Pooling Constants
    MAX_CONNECTIONS = 500
    MAX_KEEPALIVE_CONNECTIONS = 400
    KEEPALIVE_SECONDS = 300
    
    # Timeout Configuration (seconds)
    REQUEST_TIMEOUT = 120
    READ_TIMEOUT = 60
    CONNECT_TIMEOUT = 30
    
    def __init__(self, config: EngineConfig):
        """Initialize the LLM engine with configuration.
        
        Args:
            config: Engine configuration with network settings
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._stats = self._collect_stats()
        self._logger = BenchmarkLogger(f"benchmark.engine.{config.model}")
        
        # Initialize httpx.AsyncClient with configuration from EngineConfig
        # Using config.timeout for connect timeout, config.timeout for overall timeout
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=config.timeout,
                read=config.timeout,
                write=config.timeout,
            ),
            limits=httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
            ),
            keepalive=config.keepalive_timeout,
            keepalive_options=httpx.KeepaliveOptions(
                max_connections=config.max_connections,
                idle_timeout=config.keepalive_timeout,
            ),
            follow_redirects=True,
            # Retry configuration using backoff factor from config
            retry=httpx.Retry(
                total=config.max_retries,
                max_retries=config.max_retries,
                backoff_factor=config.retry_backoff,
                backoff_max=config.timeout,
            ),
        )
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the httpx.AsyncClient instance.
        
        Returns:
            The configured httpx.AsyncClient with connection pooling enabled
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=self.config.timeout,
                    read=self.config.timeout,
                    write=self.config.timeout,
                ),
                limits=httpx.Limits(
                    max_connections=self.config.max_connections,
                    max_keepalive_connections=self.config.max_keepalive_connections,
                ),
                keepalive=self.config.keepalive_timeout,
                keepalive_options=httpx.KeepaliveOptions(
                    max_connections=self.config.max_connections,
                    idle_timeout=self.config.keepalive_timeout,
                ),
                follow_redirects=True,
                # Retry configuration using backoff factor from config
                retry=httpx.Retry(
                    total=self.config.max_retries,
                    max_retries=self.config.max_retries,
                    backoff_factor=self.config.retry_backoff,
                    backoff_max=self.config.timeout,
                ),
            )
        return self._client
    
    @property
    def logger(self) -> BenchmarkLogger:
        """Get benchmark logger for this engine."""
        return self._logger
    
    @property
    def stats(self) -> dict:
        """Get current engine statistics."""
        return self._collect_stats()
    
    def _collect_stats(self) -> dict:
        """Collect current engine statistics."""
        return {
            "model": self.config.model,
            "base_url": self.config.base_url,
            "connection_pool": {
                "max_connections": self.MAX_CONNECTIONS,
                "max_keepalive_connections": self.MAX_KEEPALIVE_CONNECTIONS,
                "keepalive_seconds": self.KEEPALIVE_SECONDS,
            },
            "timeout_config": {
                "request_timeout": self.REQUEST_TIMEOUT,
                "read_timeout": self.READ_TIMEOUT,
                "connect_timeout": self.CONNECT_TIMEOUT,
            },
        }
    
    def reset_stats(self) -> None:
        """Reset engine statistics."""
        self._stats = self._collect_stats()
    
    async def close(self) -> None:
        """Close the httpx.AsyncClient and release resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            self._logger.info("Client closed successfully")
    
    @asynccontextmanager
    async def session(self) -> AsyncIterator["BaseLLMEngine"]:
        """Context manager for persistent client session.
        
        This ensures the httpx.AsyncClient is properly initialized and closed
        when the session ends, maintaining KV-cache state across requests.
        
        Usage:
            async with engine.session() as sess:
                result = await sess.generate(prompt)
        """
        try:
            yield self
        finally:
            await self.close()
    
    async def benchmark(
        self,
        prompts: list[str],
        max_tokens: int,
    ) -> list[EngineResult]:
        """Run benchmark on a set of prompts.
        
        Args:
            prompts: List of prompt strings to benchmark
            max_tokens: Maximum tokens to generate per response
            
        Returns:
            List of EngineResult objects for each prompt
        """
        results = []
        for prompt in prompts:
            try:
                response = await self._generate(prompt, max_tokens)
                result = EngineResult(
                    prompt=prompt,
                    response=response,
                    success=True,
                    metrics=None,
                )
                results.append(result)
            except Exception as e:
                results.append(EngineResult(
                    prompt=prompt,
                    response=None,
                    success=False,
                    error=str(e),
                    metrics=None,
                ))
        
        return results
    
    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        return await self._generate(prompt, max_tokens)
    
    async def _generate(self, prompt: str, max_tokens: int) -> str:
        """Internal generation method that issues HTTP request.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
            
        Raises:
            HTTPException: On failed API response
            GenerationError: On generation errors
        """
        import httpx
        import backoff
        
        retry_decorator = backoff.on_exception(
            backoff.expo,
            (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException),
            max_tries=self.config.max_retries,
            max_value=self.config.timeout,
        )
        
        @retry_decorator
        async def _do_generate() -> str:
            async with self.session() as engine:
                # Use client's request method which handles connection reuse
                response = await engine.client.request(
                    "POST",
                    engine.config.base_url,
                    json={
                        "model": engine.config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                )
                
                response.raise_for_status()
                data = response.json()
                
                self._logger.debug(f"Generated response for {len(prompt)} chars")
                return data["choices"][0]["message"]["content"]
        
        return await _do_generate()
    
    def get_status(self) -> dict:
        """Get engine status as a dictionary."""
        return {
            "name": "BaseLLMEngine",
            "config": {
                "model": self.config.model,
                "base_url": self.config.base_url,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
            "stats": self._collect_stats(),
        }
    
    def __enter__(self) -> "BaseLLMEngine":
        """Enter context manager for synchronous usage."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing the client."""
        asyncio.get_event_loop().run_until_complete(self.close())
