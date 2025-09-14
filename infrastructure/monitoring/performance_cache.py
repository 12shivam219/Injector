"""
Performance Cache Module
Provides caching decorators and cache management for performance optimization
"""

import time
import hashlib
import functools
from typing import Any, Dict, Optional, Callable
from threading import Lock

# Global cache storage
_cache_storage: Dict[str, Dict[str, Any]] = {}
_cache_lock = Lock()
_cache_stats = {
    'hits': 0,
    'misses': 0,
    'evictions': 0
}

class CacheManager:
    """Manages application-wide caching"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._timestamps = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                _cache_stats['misses'] += 1
                return None
            
            # Check TTL
            if time.time() - self._timestamps[key] > self.ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                _cache_stats['misses'] += 1
                return None
            
            _cache_stats['hits'] += 1
            return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        with self._lock:
            # Evict old entries if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                _cache_stats['evictions'] += 1
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': _cache_stats['hits'],
                'misses': _cache_stats['misses'],
                'evictions': _cache_stats['evictions'],
                'hit_rate': _cache_stats['hits'] / max(1, _cache_stats['hits'] + _cache_stats['misses'])
            }

# Global cache manager instance
_cache_manager = CacheManager()

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    return _cache_manager

def cache_key_for_file(file_obj, additional_params: Optional[Dict] = None) -> str:
    """Generate cache key for file objects"""
    try:
        # Try to get file content for hashing
        if hasattr(file_obj, 'read'):
            content = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)  # Reset file pointer
            content_hash = hashlib.md5(content).hexdigest()
        elif hasattr(file_obj, 'name'):
            content_hash = hashlib.md5(str(file_obj.name).encode()).hexdigest()
        else:
            content_hash = hashlib.md5(str(file_obj).encode()).hexdigest()
        
        # Include additional parameters in key
        if additional_params:
            params_str = str(sorted(additional_params.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"file_{content_hash}_{params_hash}"
        
        return f"file_{content_hash}"
    
    except Exception:
        # Fallback to simple string representation
        return f"file_{hashlib.md5(str(file_obj).encode()).hexdigest()}"

def cached(ttl_seconds: int = 3600, key_func: Optional[Callable] = None):
    """
    Caching decorator for functions
    
    Args:
        ttl_seconds: Time to live for cached results
        key_func: Optional function to generate cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"{func.__name__}_{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = _cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache_manager.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator

def clear_cache():
    """Clear all cached data"""
    _cache_manager.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    return _cache_manager.get_stats()

# Convenience functions for common caching patterns
def cache_function_result(func: Callable, *args, **kwargs) -> Any:
    """Cache the result of a function call"""
    cache_key = f"{func.__name__}_{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
    
    cached_result = _cache_manager.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    result = func(*args, **kwargs)
    _cache_manager.set(cache_key, result)
    return result

def invalidate_cache_pattern(pattern: str):
    """Invalidate cache entries matching a pattern"""
    with _cache_manager._lock:
        keys_to_remove = [key for key in _cache_manager._cache.keys() if pattern in key]
        for key in keys_to_remove:
            del _cache_manager._cache[key]
            del _cache_manager._timestamps[key]
