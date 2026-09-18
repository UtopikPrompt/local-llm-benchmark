import hashlib
from pathlib import Path


class BuildManager:
    """Incremental build manager."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def get_hash(self, file: Path) -> str:
        """Get file hash for incremental builds."""
        with open(file, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def should_rebuild(self) -> bool:
        """Check if rebuild is needed."""
        # Get hashes of all source files
        source_hashes = {
            self.get_hash(file): file
            for file in self.workspace.rglob("*.py")
            if file.is_file()
        }
        
        # Compare with previous build
        if self._cache.get("hashes") != source_hashes:
            self._cache["hashes"] = source_hashes
            return True
        
        return False
    
    def cache(self, key: str, value):
        """Cache build result."""
        import pickle
        import json
        
        cache_file = self.workspace / ".build_cache" / f"{key}.pkl"
        cache_file.parent.mkdir(exist_ok=True)
        
        with open(cache_file, "wb") as f:
            pickle.dump(value, f)
    
    def load_cache(self, key: str):
        """Load build cache."""
        import pickle
        
        cache_file = self.workspace / ".build_cache" / f"{key}.pkl"
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None
