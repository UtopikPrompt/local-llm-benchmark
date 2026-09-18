"""Memory management and monitoring utilities."""

import gc
import tracemalloc
import weakref
from contextlib import contextmanager
from typing import Optional


class MemoryMonitor:
    """Memory usage monitoring and management.
    
    Provides comprehensive memory tracking using tracemalloc and
garbage collection utilities.
    
    Example:
        >>> monitor = MemoryMonitor()
        >>> monitor.start()
        >>> # Your code here
        >>> monitor.report()
        >>> monitor.stop()
    """
    
    def __init__(self):
        """Initialize the memory monitor."""
        self.tracemalloc.start()
    
    def snapshot(self) -> tuple:
        """Take memory snapshot.
        
        Returns:
            Tuple of (current_size, peak_size) in bytes
        """
        current, peak = tracemalloc.get_traced_memory()
        return current, peak
    
    def report(self) -> None:
        """Print memory report."""
        current, peak = self.snapshot()
        gc.collect()
        
        print(f"\n=== Memory Report ===")
        print(f"Current: {current / 1024 / 1024:.2f} MB")
        print(f"Peak: {peak / 1024 / 1024:.2f} MB")
        print(f"GC collected: {gc.get_count()}")
        print(f"Traced objects: {gc.get_objects()}")
        print("=" * 40 + "\n")
    
    def force_gc(self) -> None:
        """Force garbage collection."""
        gc.collect()


class MemoryLeakDetector:
    """Detect potential memory leaks by tracking object growth."""
    
    def __init__(self, interval: float = 1.0):
        """Initialize the leak detector.
        
        Args:
            interval: Report interval in seconds
        """
        self.interval = interval
        self.monitor = MemoryMonitor()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start continuous monitoring."""
        import threading
        
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def _run(self) -> None:
        """Background monitoring loop."""
        import time
        last_report = time.time()
        
        while self._running:
            time.sleep(self.interval)
            
            if time.time() - last_report >= self.interval:
                self.monitor.report()
                last_report = time.time()


class TracedContext:
    """Context manager for memory tracing."""
    
    def __enter__(self) -> MemoryMonitor:
        """Enter the context."""
        return MemoryMonitor()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context."""
        monitor = MemoryMonitor()
        with monitor:
            pass


class ResourceCleaner:
    """Context manager for automatic resource cleanup."""
    
    def __init__(self, resources: dict):
        """Initialize resource cleaner.
        
        Args:
            resources: Dictionary of resource names to cleanup functions
        """
        self.resources = resources
        self._cleaned = False
    
    def __enter__(self) -> None:
        """Enter context - no action needed."""
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context - cleanup resources."""
        if not self._cleaned:
            self._cleaned = True
            for name, cleanup in self.resources.items():
                try:
                    cleanup()
                except Exception:
                    pass  # Silently ignore cleanup errors


class WeakRefHolder:
    """Safe holder for weak references to avoid memory leaks."""
    
    def __init__(self):
        """Initialize the weak reference holder."""
        self._refs: dict = {}
    
    def add(self, obj, name: str = None) -> weakref.ref:
        """Add a weak reference to an object.
        
        Args:
            obj: Object to reference
            name: Optional identifier for the reference
            
        Returns:
            The weak reference
        """
        if name is None:
            name = id(obj)
        
        ref = weakref.ref(obj, lambda ref: self._on_delete(name, ref))
        self._refs[name] = ref
        return ref
    
    def _on_delete(self, name, ref) -> None:
        """Handle object deletion."""
        if name in self._refs:
            del self._refs[name]
    
    def get(self, name: str) -> Optional[object]:
        """Get the referenced object.
        
        Args:
            name: Identifier for the reference
            
        Returns:
            The object if alive, None otherwise
        """
        ref = self._refs.get(name)
        return ref() if ref else None
    
    def remove(self, name: str) -> None:
        """Remove a reference by name."""
        if name in self._refs:
            del self._refs[name]
    
    def clear(self) -> None:
        """Remove all references."""
        self._refs.clear()
    
    def __len__(self) -> int:
        """Return number of active references."""
        return sum(1 for ref in self._refs.values() if ref() is not None)
