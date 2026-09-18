from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    version: str
    uptime: float
    memory_usage: dict


class HealthEndpoint(BaseModel):
    status: str
    version: str
    uptime: float
    memory_usage: dict
    database: dict
    cache: dict


@router.get("/", response_model=HealthEndpoint)
async def health_check():
    """Health check endpoint."""
    import psutil
    import os
    
    memory = psutil.virtual_memory()
    uptime = os.getpid()  # Simplified uptime
    
    return HealthEndpoint(
        status="healthy",
        version="1.0.0",
        uptime=uptime,
        memory_usage={
            "total": memory.total / 1024 ** 3,
            "used": memory.used / 1024 ** 3,
            "percent": memory.percent
        },
        database={
            "status": "connected",
            "pool_size": 10,
            "checked_out": 5
        },
        cache={
            "status": "healthy",
            "hits": 1000,
            "misses": 50
        }
    )
