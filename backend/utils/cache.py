"""
Caching utilities for reducing redundant API calls and computations
"""
import pickle
import time
import logging
from pathlib import Path
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, Dict
import hashlib
import json

logger = logging.getLogger(__name__)


class FileCache:
    """File-based cache for storing data between runs"""
    
    def __init__(self, cache_dir: str = "data/cache", default_ttl: int = 86400):
        """
        Initialize file cache
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a given key"""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if cache is expired
            if time.time() - cache_data['timestamp'] > cache_data['ttl']:
                logger.debug(f"Cache expired for key: {key}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return cache_data['value']
        except Exception as e:
            logger.warning(f"Failed to read cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        cache_path = self._get_cache_path(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            cache_data = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Failed to write cache for key {key}: {e}")
    
    def delete(self, key: str):
        """Delete a cache entry"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Deleted cache for key: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        logger.info("Cleared all cache entries")


# Global file cache instance
_global_cache: Optional[FileCache] = None


def get_file_cache() -> FileCache:
    """Get or create the global file cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = FileCache()
    return _global_cache


def cached(ttl: int = 86400, cache_key_func: Optional[Callable] = None):
    """
    Decorator for caching function results to file
    
    Args:
        ttl: Time-to-live in seconds
        cache_key_func: Optional function to generate cache key from args/kwargs
    
    Example:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            # Your expensive computation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Default: use function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cache = get_file_cache()
            cached_value = cache.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Export commonly used lru_cache for in-memory caching
memory_cache = lru_cache
