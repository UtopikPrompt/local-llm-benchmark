from pydantic import BaseModel

# --- Response Schemas ---

class EngineInfo(BaseModel):
    """Schema for a single engine in a list."""
    name: str
    base_url: str
    model: str

class ConfigResponse(BaseModel):
    """Schema for the /api/config POST endpoint response."""
    engines: list[EngineInfo]
    models: list[str]

class ModelListResponse(BaseModel):
    """Schema for the /api/models POST endpoint response."""
    models: list[str]

class EngineListResponse(BaseModel):
    """Schema for listing configured engines (used by /api/engines and /api/config/engines)."""
    engines: list[EngineInfo]

class BenchmarkResultsResponse(BaseModel):
    """Schema for benchmark results from /api/results."""
    results: list[dict] # Placeholder: Assuming a list of dictionaries for results data

class TaskResponse(BaseModel):
    """Schema for the /api/tasks endpoint."""
    tasks: dict