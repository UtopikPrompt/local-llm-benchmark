from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from local_llm_benchmark.middleware import (
    rate_limit_handler, 
    rate_limit_middleware,
    cors_middleware,
    cors_config
)
from local_llm_benchmark.auth import UserAuthenticator, get_current_user
from local_llm_benchmark.runner import create_app

# Create FastAPI app
app = create_app()

# Add FastAPI's built-in CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom CORS middleware
app.add_middleware(
    CORSMiddleware,
    config=cors_config
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter
)

# Add authentication middleware
app.add_middleware(UserAuthenticator)

# Add rate limit handler as dependency
from typing import AsyncGenerator

async def rate_limit_dependency(request):
    yield request

# Register the rate limit dependency
app.dependency_overrides[rate_limit_handler] = rate_limit_handler

print("API server started with rate limiting enabled!")
print("Rate limit: 100 requests per endpoint, 10 tokens/second refill rate")
