"""OpenAI-compatible LLM engine implementation.

This engine provides an OpenAI-compatible REST API interface over
httpx.AsyncClient, enabling seamless integration with tools and
libraries that expect the OpenAI format.

OpenAI API Compatibility Layer:
- Compatible with `openai-python` client
- Supports chat completions, embeddings, and file operations
- Proper error mapping to OpenAI-style exceptions
- Streaming response support
"""

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx
from httpx import AsyncStream, Response

from ..logger import BenchmarkLogger, logger
from ..schemas.engine import EngineConfig, EngineResult
from ..schemas.response import Choice, LLMResponse


class OpenAICompatEngine:
    """OpenAI-compatible LLM engine.
    
    Wraps an httpx.AsyncClient to provide OpenAI-compatible REST API.
    Supports chat completions with streaming and proper error handling.
    
    Attributes:
        config: Engine configuration
        client: httpx.AsyncClient instance
        logger: Benchmark logger
    """
    
    # OpenAI API Constants
    BASE_PATH = "/v1"
    MODEL_PATH = "chat/completions"
    EMBEDDINGS_PATH = "embeddings"
    
    # Default OpenAI parameters
    DEFAULT_PARAMS = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4096,
        "stream": False,
    }
    
    def __init__(self, config: EngineConfig):
        """Initialize the OpenAI-compatible engine.
        
        Args:
            config: Engine configuration with base_url and model
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._logger = BenchmarkLogger(f"benchmark.engine.{config.model}")
        self._stats = self._collect_stats()
        
        # Initialize httpx.AsyncClient with optimized settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                request=config.max_requests * 60,  # 60s per request
                read=config.max_response_size / 1024 / 1024 * 1000,  # ~100KB read timeout
            ),
            limits=httpx.Limits(
                max_connections=config.max_keepalive_connections,
                max_keepalive_connections=config.max_keepalive_connections,
            ),
            keepalive=config.keepalive_timeout,
            follow_redirects=True,
        )
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the httpx.AsyncClient instance."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    request=self.config.max_requests * 60,
                    read=self.config.max_response_size / 1024 / 1024 * 1000,
                ),
                limits=httpx.Limits(
                    max_connections=self.config.max_keepalive_connections,
                    max_keepalive_connections=self.config.max_keepalive_connections,
                ),
                keepalive=self.config.keepalive_timeout,
                follow_redirects=True,
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
                "max_connections": self.config.max_keepalive_connections,
                "max_keepalive_connections": self.config.max_keepalive_connections,
                "keepalive_seconds": self.config.keepalive_timeout,
            },
            "timeout_config": {
                "request_timeout": self.config.max_requests * 60,
                "read_timeout": self.config.max_response_size / 1024 / 1024 * 1000,
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
    async def session(self) -> AsyncIterator["OpenAICompatEngine"]:
        """Context manager for persistent client session."""
        try:
            yield self
        finally:
            await self.close()
    
    async def benchmark(self, prompts: list[str], max_tokens: int) -> list[EngineResult]:
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
        """
        async with self.session() as engine:
            response = await engine.client.post(
                f"{engine.config.base_url}{self.MODEL_PATH}",
                json=self._build_request(prompt, max_tokens),
            )
            response.raise_for_status()
            data = response.json()
            
            self._logger.debug(f"Generated response for {len(prompt)} chars")
            return data["choices"][0]["message"]["content"]
    
    def _build_request(self, prompt: str, max_tokens: int) -> dict:
        """Build OpenAI-compatible chat completion request.
        
        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            
        Returns:
            OpenAI-compatible request dictionary
        """
        request = {
            "model": self.config.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
        }
        
        # Apply engine configuration
        request["temperature"] = self.config.temperature
        request["top_p"] = self.config.top_p
        
        # Apply extra headers
        for key, value in self.config.extra_headers.items():
            request["headers"][key] = value
        
        return request
    
    async def list_models(self) -> list[str]:
        """List available models.
        
        Returns:
            List of model names available on this engine
        """
        try:
            response = await self.client.get(f"{self.config.base_url}{self.BASE_PATH}/models")
            response.raise_for_status()
            data = response.json()
            
            self._logger.info(f"Listed {len(data.get('data', []))} models")
            return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            self._logger.warning(f"Failed to list models: {e}")
            return [self.config.model]  # Return configured model as fallback
    
    def _format_usage(self, usage: dict) -> dict:
        """Format OpenAI usage to standard format."""
        total = usage.get("total_tokens", 0)
        completion = total - usage.get("prompt_tokens", 0)
        
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": completion,
            "total_tokens": total,
        }
    
    def _format_response(self, data: dict) -> LLMResponse:
        """Format OpenAI response to LLMResponse."""
        return LLMResponse(
            id=data.get("id"),
            model=data.get("model"),
            choices=[
                Choice(
                    index=choice["index"],
                    message={"content": choice["message"], "role": choice.get("role", "assistant")},
                    finish_reason=choice.get("finish_reason"),
                    logprobs=choice.get("logprobs"),
                )
                for choice in data.get("choices", [])
            ],
            usage=self._format_usage(data.get("usage", {})),
            system_fingerprint=data.get("system_fingerprint"),
            created=data.get("created"),
        )
    
    def get_status(self) -> dict:
        """Get engine status as a dictionary."""
        return {
            "name": "OpenAICompatEngine",
            "config": {
                "model": self.config.model,
                "base_url": self.config.base_url,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
            "stats": self._collect_stats(),
        }
    
    def __enter__(self) -> "OpenAICompatEngine":
        """Enter context manager for synchronous usage."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing the client."""
        asyncio.get_event_loop().run_until_complete(self.close())


class OpenAIError(Exception):
    """Base exception for OpenAI API errors."""
    pass


class OpenAIErrorHTTPError(OpenAIError):
    """Exception raised for HTTP errors from OpenAI API."""
    pass


class OpenAIErrorAPIError(OpenAIError):
    """Exception raised for API errors from OpenAI API."""
    def __init__(self, message: str, response: Optional[Response] = None):
        super().__init__(message)
        self.response = response
        self.code = response.status_code if response else None


class OpenAIErrorRateLimit(OpenAIError):
    """Exception raised for rate limit errors."""
    pass


class OpenAIErrorTimeout(OpenAIError):
    """Exception raised for timeout errors."""
    pass


@asynccontextmanager
async def openai_stream(
    engine: "OpenAICompatEngine",
    request: dict,
) -> AsyncIterator[Union[Response, str]]:
    """Streaming context manager for OpenAI API.
    
    Yields:
        - Response objects for non-streaming requests
        - String chunks for streaming requests
    
    Usage:
        async with openai_stream(engine, request) as chunk:
            await chunk
    """
    try:
        response = await engine.client.post(
            f"{engine.config.base_url}{engine.MODEL_PATH}",
            json=request,
            stream=True,
        )
        response.raise_for_status()
        
        async def stream_generator() -> AsyncIterator[str]:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    if data:
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            pass
        
        async for chunk in stream_generator():
            yield chunk
    except Exception as e:
        raise OpenAIErrorHTTPError(str(e)) from e


__all__ = [
    "OpenAICompatEngine",
    "OpenAIError",
    "OpenAIErrorHTTPError",
    "OpenAIErrorAPIError",
    "OpenAIErrorRateLimit",
    "OpenAIErrorTimeout",
    "openai_stream",
]
