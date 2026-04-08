"""Forecast caching service for prediction results.

Caches forecasts to avoid repeated inference and provides
TTL-based invalidation for keeping predictions fresh.
"""

from datetime import datetime, timedelta
from typing import Optional
import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class ForecastCache:
    """Cache for storing and retrieving forecast results."""

    def __init__(self, redis_client: Redis, default_ttl_hours: int = 24):
        """Initialize the forecast cache.

        Args:
            redis_client: Async Redis client for caching.
            default_ttl_hours: Default time-to-live for cached forecasts.
        """
        self._redis = redis_client
        self._default_ttl = timedelta(hours=default_ttl_hours)
        self._key_prefix = "forecast:"

    def _make_key(
        self,
        user_id: str,
        forecast_type: str,
        entity_id: Optional[str] = None,
    ) -> str:
        """Generate a cache key for a forecast."""
        parts = [self._key_prefix, user_id, forecast_type]
        if entity_id:
            parts.append(entity_id)
        return ":".join(parts)

    async def get(
        self,
        user_id: str,
        forecast_type: str,
        entity_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Retrieve a cached forecast.

        Args:
            user_id: User identifier.
            forecast_type: Type of forecast (activity, entity, relationship, graph).
            entity_id: Optional entity identifier for entity-specific forecasts.

        Returns:
            Cached forecast data or None if not found/expired.
        """
        key = self._make_key(user_id, forecast_type, entity_id)
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
        return None

    async def set(
        self,
        user_id: str,
        forecast_type: str,
        data: dict,
        entity_id: Optional[str] = None,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """Store a forecast in cache.

        Args:
            user_id: User identifier.
            forecast_type: Type of forecast.
            data: Forecast data to cache.
            entity_id: Optional entity identifier.
            ttl: Custom time-to-live (uses default if not provided).

        Returns:
            True if cached successfully.
        """
        key = self._make_key(user_id, forecast_type, entity_id)
        ttl = ttl or self._default_ttl
        try:
            cache_data = {
                "data": data,
                "cached_at": datetime.utcnow().isoformat(),
            }
            await self._redis.setex(
                key,
                int(ttl.total_seconds()),
                json.dumps(cache_data),
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def invalidate(
        self,
        user_id: str,
        forecast_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> int:
        """Invalidate cached forecasts.

        Args:
            user_id: User identifier.
            forecast_type: Optional type to invalidate (all types if None).
            entity_id: Optional entity to invalidate.

        Returns:
            Number of keys invalidated.
        """
        if forecast_type and entity_id:
            key = self._make_key(user_id, forecast_type, entity_id)
            result = await self._redis.delete(key)
            return result
        
        pattern = f"{self._key_prefix}{user_id}:"
        if forecast_type:
            pattern += f"{forecast_type}:*"
        else:
            pattern += "*"
        
        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self._redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")
        return 0

    async def get_all_user_forecasts(self, user_id: str) -> dict[str, dict]:
        """Get all cached forecasts for a user.

        Args:
            user_id: User identifier.

        Returns:
            Dictionary mapping forecast types to their cached data.
        """
        pattern = f"{self._key_prefix}{user_id}:*"
        results = {}
        try:
            async for key in self._redis.scan_iter(match=pattern):
                data = await self._redis.get(key)
                if data:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    forecast_type = key_str.split(":")[-1]
                    results[forecast_type] = json.loads(data)
        except Exception as e:
            logger.warning(f"Error fetching all forecasts for {user_id}: {e}")
        return results
