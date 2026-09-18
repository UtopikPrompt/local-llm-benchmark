"""API module with OpenAPI documentation and schemas."""

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_url, get_swagger_ui_url

app = FastAPI(
    title="Local LLM Benchmark API",
    description="""
    ## API Documentation
    
    This API provides endpoints for running and managing LLM benchmarks.
    
    ### Authentication
    
    Authentication is not required for this version of the API.
    
    ### Rate Limiting
    
    Requests are rate limited to prevent overwhelming LLM services.
    """,
    version="1.0.0"
)

# Add documentation URLs
app.add_api_route("/docs", get_swagger_ui_url, include_in_schema=False)
app.add_api_route("/redoc", get_redoc_url, include_in_schema=False)

__all__ = ["app"]
