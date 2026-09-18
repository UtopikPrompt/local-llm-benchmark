"""Streaming response with automatic cleanup."""

from typing import Any, AsyncIterator


class StreamingResponse:
    """Streaming response with automatic cleanup.
    
    A context manager for streaming responses that automatically
    cleans up resources when streaming completes or when closed.
    
    Example:
        async with StreamingResponse(data) as response:
            async for chunk in response:
                await output.write(chunk)
    
    Example:
        async def stream_data(items):
            async with StreamingResponse(items) as response:
                async for chunk in response.__aiter__():
                    yield chunk
    """
    
    def __init__(self, data: list):
        """Initialize the streaming response.
        
        Args:
            data: List of items to stream
        """
        self._data = data
        self._iterator = iter(data)
    
    async def __aiter__(self) -> AsyncIterator[Any]:
        """Async iterator for streaming data.
        
        Yields each item in the data list one at a time.
        """
        for chunk in self._iterator:
            yield chunk
        
        # Cleanup after streaming completes
        self._iterator = None
        self._data = None
    
    def close(self) -> None:
        """Manually close and cleanup."""
        self._iterator = None
        self._data = None
    
    def __len__(self) -> int:
        """Return total number of items."""
        return len(self._data)
    
    def __bool__(self) -> bool:
        """Return True if there are items to stream."""
        return self._iterator is not None


class AsyncContextManager:
    """Base class for async context managers with cleanup."""
    
    def __init__(self, data: Any):
        """Initialize with data to clean up."""
        self._data = data
        self._cleanup_done = False
    
    async def __aenter__(self) -> "AsyncContextManager":
        """Enter async context."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context with cleanup."""
        if not self._cleanup_done:
            self._cleanup_done = True
            await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Perform cleanup."""
        pass
    
    def close(self) -> None:
        """Synchronous cleanup."""
        pass


class TracedContextManager(AsyncContextManager):
    """Async context manager with memory tracing."""
    
    def __init__(self, data: Any):
        super().__init__(data)
        from local_llm_benchmark.utils.memory import MemoryMonitor
        self._monitor = MemoryMonitor()
    
    async def __aenter__(self) -> "TracedContextManager":
        """Enter with memory monitoring."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit with memory report."""
        await super().__aexit__(exc_type, exc_val, exc_tb)
        self._monitor.report()


class ResponseStream:
    """Simple response stream wrapper."""
    
    def __init__(self, generator: AsyncIterator):
        """Initialize with async generator."""
        self._generator = generator
        self._iterator = self._generator
    
    async def __aiter__(self) -> AsyncIterator:
        """Async iterator."""
        async for item in self._iterator:
            yield item
    
    def close(self) -> None:
        """Close the generator."""
        self._iterator = None
