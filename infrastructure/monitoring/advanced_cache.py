"""
Advanced Cache Management Module
Provides multi-level caching functionality for performance optimization
"""

import time
import logging
import threading
import functools
from typing import Any, Optional, Dict, List, Tuple, Callable, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheLevel(Enum):
    """Cache level types"""
    MEMORY = "memory"
    PERSISTENT = "persistent"
    ALL = "all"

@dataclass
class CacheStats:
    """Statistics for cache performance monitoring"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    last_cleanup: Optional[datetime] = None

class MemoryCache:
    """Enhanced in-memory cache with LRU eviction and statistics"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.stats = CacheStats(max_size=max_size)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with statistics tracking"""
        with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None
            
            entry = self._cache[key]
            if time.time() > entry['expires']:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                self.stats.evictions += 1
                self.stats.misses += 1
                return None
            
            # Update access time for LRU
            self._access_times[key] = time.time()
            self.stats.hits += 1
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL and eviction if needed"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
            self._access_times[key] = time.time()
            self.stats.size = len(self._cache)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries"""
        if not self._access_times:
            return
        
        # Find oldest entry
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        # Remove it
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
        self.stats.evictions += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                self.stats.size = len(self._cache)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self.stats.size = 0
            self.stats.last_cleanup = datetime.now()
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of removed items"""
        now = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if now > entry['expires']
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                removed += 1
            
            self.stats.evictions += removed
            self.stats.size = len(self._cache)
            self.stats.last_cleanup = datetime.now()
        
        return removed
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        with self._lock:
            self.stats.size = len(self._cache)
            return self.stats

class AdvancedCacheManager:
    """
    Advanced cache manager with multi-level caching support
    and namespace isolation
    """
    
    def __init__(self):
        # Primary memory cache with namespaces
        self._memory_caches: Dict[str, MemoryCache] = {}
        self._default_namespace = "default"
        self._lock = threading.RLock()
        
        # Create default namespace
        self._get_or_create_cache(self._default_namespace)
    
    def _get_or_create_cache(self, namespace: str) -> MemoryCache:
        """Get or create a cache for the specified namespace"""
        with self._lock:
            if namespace not in self._memory_caches:
                self._memory_caches[namespace] = MemoryCache()
            return self._memory_caches[namespace]
    
    def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """Get value from cache with optional namespace"""
        namespace = namespace or self._default_namespace
        cache = self._get_or_create_cache(namespace)
        return cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = None) -> None:
        """Set value in cache with optional namespace and TTL"""
        namespace = namespace or self._default_namespace
        cache = self._get_or_create_cache(namespace)
        cache.set(key, value, ttl)
    
    def delete(self, key: str, namespace: str = None) -> bool:
        """Delete key from cache with optional namespace"""
        namespace = namespace or self._default_namespace
        if namespace in self._memory_caches:
            return self._memory_caches[namespace].delete(key)
        return False
    
    def clear(self, namespace: str = None) -> None:
        """Clear cache entries with optional namespace"""
        with self._lock:
            if namespace:
                if namespace in self._memory_caches:
                    self._memory_caches[namespace].clear()
            else:
                # Clear all namespaces
                for cache in self._memory_caches.values():
                    cache.clear()
    
    def cleanup_expired(self, namespace: str = None) -> int:
        """Clean up expired entries with optional namespace"""
        total_removed = 0
        
        with self._lock:
            if namespace:
                if namespace in self._memory_caches:
                    total_removed = self._memory_caches[namespace].cleanup_expired()
            else:
                # Clean up all namespaces
                for cache in self._memory_caches.values():
                    total_removed += cache.cleanup_expired()
        
        return total_removed
    
    def get_stats(self, namespace: str = None) -> Dict[str, Any]:
        """Get cache statistics with optional namespace"""
        stats = {}
        
        with self._lock:
            if namespace:
                if namespace in self._memory_caches:
                    stats[namespace] = self._memory_caches[namespace].get_stats().__dict__
            else:
                # Get stats for all namespaces
                for ns, cache in self._memory_caches.items():
                    stats[ns] = cache.get_stats().__dict__
                
                # Add aggregate stats
                total_hits = sum(s.hits for s in (cache.get_stats() for cache in self._memory_caches.values()))
                total_misses = sum(s.misses for s in (cache.get_stats() for cache in self._memory_caches.values()))
                total_size = sum(s.size for s in (cache.get_stats() for cache in self._memory_caches.values()))
                
                stats["_aggregate"] = {
                    "hits": total_hits,
                    "misses": total_misses,
                    "size": total_size,
                    "hit_ratio": total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
                }
        
        return stats

# Global cache instance
_advanced_cache = AdvancedCacheManager()

def get_advanced_cache_manager() -> AdvancedCacheManager:
    """Get global advanced cache manager instance"""
    return _advanced_cache

def cached(ttl: int = 300, namespace: str = None, key_pattern: str = None):
    """
    Decorator to cache function results with advanced options
    
    Args:
        ttl: Time to live in seconds
        namespace: Cache namespace
        key_pattern: Custom key pattern with {arg_name} placeholders
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_pattern:
                # Get function argument names
                arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
                
                # Create mapping of arg names to values
                arg_dict = dict(zip(arg_names, args))
                arg_dict.update(kwargs)
                
                try:
                    # Format key using pattern
                    cache_key = key_pattern.format(**arg_dict)
                except (KeyError, IndexError):
                    # Fallback if formatting fails
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            else:
                # Default key generation
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = _advanced_cache.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Compute result and cache it
            result = func(*args, **kwargs)
            _advanced_cache.set(cache_key, result, ttl, namespace)
            return result
        
        # Add cache control methods to the wrapped function
        wrapper.clear_cache = lambda: _advanced_cache.clear(namespace)
        wrapper.get_stats = lambda: _advanced_cache.get_stats(namespace)
        
        return wrapper
    return decorator