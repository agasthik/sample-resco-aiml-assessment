"""
Resource caching module to avoid repeated API calls
"""
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import time

logger = logging.getLogger()


class ResourceCache:
    """
    In-memory cache for AWS resource descriptions to avoid repeated API calls
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._ttl: int = 300  # 5 minutes TTL

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if it exists and hasn't expired

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None

        # Check if cache entry has expired
        if time.time() - self._cache_timestamps.get(key, 0) > self._ttl:
            logger.debug(f"Cache expired for key: {key}")
            del self._cache[key]
            del self._cache_timestamps[key]
            return None

        logger.debug(f"Cache hit for key: {key}")
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """
        Set cache value

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        logger.debug(f"Cached value for key: {key}")

    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.debug("Cache cleared")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_entries': len(self._cache),
            'cache_size_bytes': sum(len(str(v)) for v in self._cache.values())
        }


# Global cache instance
_resource_cache = ResourceCache()


def get_cache() -> ResourceCache:
    """Get the global resource cache instance"""
    return _resource_cache


def cached_api_call(cache_key_prefix: str):
    """
    Decorator to cache AWS API call results

    Args:
        cache_key_prefix: Prefix for the cache key

    Usage:
        @cached_api_call('bedrock_guardrails')
        def list_guardrails():
            return bedrock_client.list_guardrails()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{cache_key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_value = _resource_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call the function and cache the result
            logger.debug(f"Cache miss for {cache_key}, calling API")
            result = func(*args, **kwargs)
            _resource_cache.set(cache_key, result)

            return result
        return wrapper
    return decorator


def cache_resource_list(resource_type: str, resources: list) -> None:
    """
    Cache a list of resources by type

    Args:
        resource_type: Type of resource (e.g., 'bedrock_guardrails', 'sagemaker_domains')
        resources: List of resources to cache
    """
    cache_key = f"resource_list:{resource_type}"
    _resource_cache.set(cache_key, resources)


def get_cached_resource_list(resource_type: str) -> Optional[list]:
    """
    Get cached resource list by type

    Args:
        resource_type: Type of resource

    Returns:
        Cached resource list or None
    """
    cache_key = f"resource_list:{resource_type}"
    return _resource_cache.get(cache_key)


def cache_resource_details(resource_type: str, resource_id: str, details: Dict[str, Any]) -> None:
    """
    Cache detailed information about a specific resource

    Args:
        resource_type: Type of resource
        resource_id: Unique identifier for the resource
        details: Resource details to cache
    """
    cache_key = f"resource_details:{resource_type}:{resource_id}"
    _resource_cache.set(cache_key, details)


def get_cached_resource_details(resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached resource details

    Args:
        resource_type: Type of resource
        resource_id: Unique identifier for the resource

    Returns:
        Cached resource details or None
    """
    cache_key = f"resource_details:{resource_type}:{resource_id}"
    return _resource_cache.get(cache_key)
