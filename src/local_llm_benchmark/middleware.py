"""CORS and Rate Limiting middleware for the local-llm-benchmark API.

Provides comprehensive CORS configuration and validation, plus rate limiting.
"""

import asyncio
import time
from typing import Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rate_limiter import RateLimiter, TokenBucket

from local_llm_benchmark.config import CORSConfig, TokenConfig, Role


# CORS configuration
cors_config = CORSConfig()


# Global rate limiter instance
rate_limiter = RateLimiter(default_burst=100, default_rate=10.0)


class CORSMiddleware:
    """Custom CORS middleware with validation."""
    
    def __init__(self, config: CORSConfig):
        self.config = config
    
    async def __call__(self, request: Request, call_next):
        """Middleware handler with CORS validation."""
        origin = request.headers.get("origin")
        
        # Validate origin
        if not origin:
            # No origin header - might be internal request, allow
            pass
        elif not self._is_valid_origin(origin):
            # Invalid origin
            response = JSONResponse(
                status_code=403,
                content={
                    "error": "CORS origin not allowed",
                    "allowed_origins": self.config.origins
                }
            )
            response.headers["X-Allowed-Origin"] = "None"
            return response
        
        # Handle preflight request
        if request.method == "OPTIONS":
            response = await self._handle_preflight(request)
            return response
        
        # Handle actual request
        response = await call_next()
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.config.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.config.allowed_headers)
        response.headers["Access-Control-Allow-Headers"] += f", {request.headers.get('content-type')}"
        
        # Cache control for responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        if self.config.allow_all_origins:
            return True
        
        return origin in self.config.origins
    
    async def _handle_preflight(self, request: Request) -> Response:
        """Handle CORS preflight request."""
        response = Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin"),
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": ", ".join(self.config.allowed_methods),
                "Access-Control-Allow-Headers": ", ".join(self.config.allowed_headers),
                "Access-Control-Max-Age": "86400",  # 24 hours
                "Vary": "Origin"
            }
        )
        return response


# Create CORS middleware instance
cors_middleware = CORSMiddleware(cors_config)


# Create rate limiter instance
rate_limiter = RateLimiter(default_burst=100, default_rate=10.0)


class RateLimitMiddleware:
    """Rate limiting middleware for FastAPI."""
    
    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
    
    async def __call__(self, request: Request, call_next):
        """Middleware handler."""
        endpoint = request.url.path
        
        try:
            if not await self.limiter.allow_request(endpoint):
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after": 60  # seconds
                    }
                )
                response.headers["X-RateLimit-Limit"] = "100"
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = "60"
                return response
            
            response = await call_next()
            
            # Update rate limit headers
            stats = self.limiter.get_stats(endpoint)
            response.headers["X-RateLimit-Limit"] = str(stats["capacity"])
            response.headers["X-RateLimit-Remaining"] = str(max(0, int(stats["current_tokens"]) - 1))
            
            return response
        
        except Exception as e:
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = "0"
            return response


# Create middleware instance
rate_limit_middleware = RateLimitMiddleware(rate_limiter)


async def rate_limit_handler(request: Request, call_next):
    """Async rate limit handler that can be used as FastAPI dependency."""
    endpoint = request.url.path
    
    try:
        if not await rate_limiter.allow_request(endpoint):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": 60
                }
            )
        
        response = await call_next()
        
        # Add rate limit headers
        stats = rate_limiter.get_stats(endpoint)
        response.headers["X-RateLimit-Limit"] = str(stats["capacity"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(stats["current_tokens"]) - 1))
        
        return response
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
