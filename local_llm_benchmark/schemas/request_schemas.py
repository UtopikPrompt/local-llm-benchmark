from pydantic import BaseModel

# --- Request Schemas ---

class RunRequest(BaseModel):
    """Schema for the /api/run endpoint request body."""
    # Placeholder: Populate with actual fields required for benchmark run
    benchmark_id: str
    model: str | None = None
    # Add any other fields found in the request dict here
    pass

class EngineUpdateRequest(BaseModel):
    """Schema for updating an engine, used in /api/config/engines/{name} PUT."""
    # Placeholder: Populate with actual fields required for update
    base_url: str
    model: str

class EnginePreviewRequest(BaseModel):
    """Schema for predicting engine configuration, used in /api/config POST."""
    base_url: str
    model: str

class ModelListRequest(BaseModel):
    """Schema for listing models, used in /api/models POST."""
    base_url: str

class EngineSaveRequest(BaseModel):
    """Schema for saving a new engine, used in /api/config/engines POST."""
    base_url: str
    model: str