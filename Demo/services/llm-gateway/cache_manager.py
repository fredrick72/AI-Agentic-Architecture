"""
LLM Gateway - Cache Manager
Provides 90% cost savings through intelligent caching
"""
import redis
import json
import hashlib
from typing import Optional, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache for LLM responses"""

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✓ Connected to Redis")
        except Exception as e:
            logger.warning(f"⚠ Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None

    def _generate_cache_key(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        Generate deterministic cache key from request parameters

        Args:
            prompt: User prompt text
            model: Model name
            temperature: Temperature parameter
            max_tokens: Max tokens parameter

        Returns:
            SHA256 hash as cache key
        """
        # Create a stable string representation of the request
        cache_input = f"{model}:{temperature}:{max_tokens}:{prompt}"

        # Generate SHA256 hash
        hash_obj = hashlib.sha256(cache_input.encode('utf-8'))
        cache_key = f"llm:cache:{hash_obj.hexdigest()[:16]}"

        return cache_key

    def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response if available

        Args:
            prompt: User prompt
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting

        Returns:
            Cached response dict or None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(prompt, model, temperature, max_tokens)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.info(f"✓ Cache HIT for key: {cache_key[:32]}...")
                response = json.loads(cached_data)
                response["cache_hit"] = True
                return response
            else:
                logger.info(f"⚠ Cache MISS for key: {cache_key[:32]}...")
                return None

        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    def set(
        self,
        prompt: str,
        model: str,
        response_data: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store response in cache

        Args:
            prompt: User prompt
            model: Model name
            response_data: Response data to cache
            temperature: Temperature setting
            max_tokens: Max tokens setting
            ttl: Time-to-live in seconds (default from settings)

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(prompt, model, temperature, max_tokens)
            ttl = ttl or settings.cache_ttl_seconds

            # Store as JSON with TTL
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(response_data)
            )

            logger.info(f"✓ Cached response with TTL={ttl}s: {cache_key[:32]}...")
            return True

        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    def invalidate(self, pattern: str = "llm:cache:*") -> int:
        """
        Invalidate cache entries matching pattern

        Args:
            pattern: Redis key pattern (default: all LLM cache)

        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        try:
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"✓ Invalidated {deleted} cache entries")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        if not self.redis_client:
            return {"status": "disabled"}

        try:
            info = self.redis_client.info("stats")
            keys_count = len(list(self.redis_client.scan_iter(match="llm:cache:*", count=1000)))

            return {
                "status": "connected",
                "cached_responses": keys_count,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Global cache manager instance
cache_manager = CacheManager()
