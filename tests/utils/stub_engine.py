"""StubEngine implementation for deterministic benchmark testing."""

from typing import Generator, List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import hashlib


@dataclass
class StubResponse:
    """Deterministic response for a given request."""
    content: str
    tokens_used: int
    tokens_generated: int
    time_ms: float
    cost_usd: float
    quality_score: float
    safety_score: float
    accuracy_score: float


@dataclass
class StubEngineConfig:
    """Configuration for StubEngine."""
    base_response: str = "This is a deterministic response for testing. "
    response_length: int = 50
    token_ratio: float = 0.7
    base_time_ms: float = 50.0
    base_cost_usd: float = 0.0001
    quality_base: float = 0.85
    quality_variance: float = 0.05
    safety_base: float = 0.95
    safety_variance: float = 0.02
    accuracy_base: float = 0.88
    accuracy_variance: float = 0.03
    model_name: str = "stub-model"
    
    @classmethod
    def default(cls) -> "StubEngineConfig":
        return cls()


class StubEngine:
    """
    Deterministic LLM engine stub for testing.
    
    Provides reproducible responses for the same input, enabling
    reliable testing of benchmark pipelines without external dependencies.
    
    Features:
    - Deterministic responses based on input hash
    - Configurable response parameters
    - Simulated latency and token usage
    - Pre-built response templates for common tasks
    """
    
    def __init__(self, config: StubEngineConfig = None):
        self.config = config or StubEngineConfig.default()
        self._response_cache: Dict[str, StubResponse] = {}
        self._seed = random.randint(0, 2**31 - 1)
        random.seed(self._seed)
    
    def _compute_request_hash(self, request: Dict[str, Any]) -> str:
        """Compute deterministic hash for request."""
        request_str = str(request)
        return hashlib.sha256(request_str.encode()).hexdigest()[:16]
    
    def _get_cached_response(self, request: Dict[str, Any]) -> Optional[StubResponse]:
        """Retrieve cached response if available."""
        request_hash = self._compute_request_hash(request)
        return self._response_cache.get(request_hash)
    
    def _generate_response(self, request: Dict[str, Any]) -> StubResponse:
        """Generate deterministic response for a request."""
        request_hash = self._compute_request_hash(request)
        
        # Check cache first
        cached = self._get_cached_response(request)
        if cached:
            return cached
        
        # Extract input from request
        input_text = self._extract_input(request)
        
        # Generate deterministic response based on input
        response_content = self._generate_response_content(input_text, request)
        
        # Calculate metrics
        tokens_used = self._calculate_tokens(response_content)
        tokens_generated = self._calculate_tokens(input_text) * self.config.token_ratio
        
        # Simulate latency with small variance
        time_ms = self.config.base_time_ms + random.uniform(-10, 10)
        time_ms = max(10.0, time_ms)  # Minimum 10ms
        
        # Calculate cost
        cost_usd = self.config.base_cost_usd * tokens_generated
        
        # Generate quality metrics with variance
        quality_score = max(0.0, min(1.0, 
            self.config.quality_base + random.gauss(0, self.config.quality_variance)
        ))
        safety_score = max(0.0, min(1.0, 
            self.config.safety_base + random.gauss(0, self.config.safety_variance)
        ))
        accuracy_score = max(0.0, min(1.0, 
            self.config.accuracy_base + random.gauss(0, self.config.accuracy_variance)
        ))
        
        response = StubResponse(
            content=response_content,
            tokens_used=tokens_used,
            tokens_generated=int(tokens_generated),
            time_ms=time_ms,
            cost_usd=cost_usd,
            quality_score=quality_score,
            safety_score=safety_score,
            accuracy_score=accuracy_score,
        )
        
        # Cache the response
        self._response_cache[request_hash] = response
        
        return response
    
    def _extract_input(self, request: Dict[str, Any]) -> str:
        """Extract input text from request."""
        # Try to find input in various locations
        if "input" in request:
            return str(request["input"])
        if "user_message" in request:
            return str(request["user_message"])
        if "question" in request:
            return str(request["question"])
        if "content" in request:
            return str(request["content"])
        # Default fallback
        return "default test input"
    
    def _generate_response_content(self, input_text: str, request: Dict[str, Any]) -> str:
        """Generate response content based on input and request type."""
        request_type = request.get("type", "general")
        
        # Pre-built responses for common scenarios
        prebuilt_responses = {
            "summarization": f"Summary of: {input_text[:100]}...\n\nKey points extracted from the provided text. "
                           f"This response demonstrates deterministic generation. "
                           f"Input length: {len(input_text)} characters. "
                           f"Generated content is reproducible for the same input.",
            "classification": f"Classification Result: {input_text[:50]}...\n\nPredicted category: PRIMARY\n\nConfidence: {self._format_score(0.92)}\n\nThis is a deterministic classification response. "
                            f"The same input will always produce the same output.",
            "code_generation": f"Code for: {input_text[:50]}...\n\n```python\ndef solution():\n    # Deterministic implementation\n    # Same input → Same output\n    return 'deterministic output'\n\n```\n\nThis code generation is reproducible. "
                             f"Input: {len(input_text)} characters processed.",
            "creative": f"Creative response to: {input_text[:50]}...\n\nHere is a creative response generated deterministically. "
                        f"The magic of consistency! Input: {len(input_text)} chars. "
                        f"Output: {len(self.config.base_response)} chars. "
                        f"Perfect for testing and benchmarking.",
            "reasoning": f"Reasoning trace for: {input_text[:50]}...\n\nStep 1: Analyze the input.\n" 
                         f"Step 2: Apply deterministic algorithm.\n" 
                         f"Step 3: Verify result.\n\nResult: DETERMINISTIC OUTPUT\n\nThis demonstrates reproducible reasoning. "
                         f"Input hash: {self._compute_request_hash(request)}",
            "translation": f"Translation: {input_text[:50]}...\n\nEnglish → {request.get('target_language', 'Spanish')}\n\nTranslated content generated deterministically. "
                           f"Source: {len(input_text)} characters. "
                           f"Translation is reproducible.",
        }
        
        # Use prebuilt response if available, otherwise generate generic
        if request_type in prebuilt_responses:
            return prebuilt_responses[request_type]
        
        # Generic response
        return self.config.base_response + f"Input processed: {len(input_text)} characters. " \
               f"Deterministic output for testing. Request hash: {self._compute_request_hash(request)}"
    
    def _calculate_tokens(self, text: str) -> int:
        """Estimate token count (approximate: 1 token ≈ 4 characters)."""
        return len(text) // 4 + 1
    
    def _format_score(self, score: float) -> str:
        """Format score as percentage string."""
        return f"{score * 100:.1f}%"
    
    def cleanup(self):
        """Clear response cache."""
        self._response_cache.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


@pytest.fixture
def stub_engine() -> Generator[StubEngine, None, None]:
    """Fixture to provide a StubEngine for deterministic testing."""
    engine = StubEngine()
    try:
        yield engine
    finally:
        engine.cleanup()


@pytest.fixture
def stub_engine_config() -> StubEngineConfig:
    """Fixture to provide default StubEngine configuration."""
    return StubEngineConfig.default()
