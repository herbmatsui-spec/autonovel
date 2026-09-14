import hashlib
from typing import Optional
from src.models.prose_refinement import ProseRefineResult

class RefinementCache:
    """LRU cache to prevent redundant refinement of identical expressions"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []
    
    def _get_key(self, text: str, genre: str, style_intensity: str) -> str:
        """Generate cache key"""
        key_string = f'{text}|{genre}|{style_intensity}'
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def get(self, text: str, genre: str, style_intensity: str) -> Optional[ProseRefineResult]:
        """Get refinement result from cache"""
        key = self._get_key(text, genre, style_intensity)
        if key in self.cache:
            # LRU: update access order
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, text: str, genre: str, style_intensity: str, result: ProseRefineResult) -> None:
        """Store refinement result in cache"""
        key = self._get_key(text, genre, style_intensity)
        
        # If already exists, update
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # LRU: remove oldest entry
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        # Add new entry
        self.cache[key] = result
        self.access_order.append(key)
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        self.access_order.clear()