"""
Rate limiting middleware.

This module provides middleware for implementing rate limiting on API endpoints
to prevent abuse and ensure fair usage.
"""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.exceptions import RateLimitError

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    This middleware implements rate limiting based on client IP addresses
    to prevent API abuse and ensure fair usage.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests: int = 100,
        window: int = 60,
        skip_paths: list = None,
        use_redis: bool = False,
        redis_url: str = None,
    ) -> None:
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI application
            requests: Number of requests allowed in the time window
            window: Time window in seconds
            skip_paths: List of paths to skip rate limiting
            use_redis: Whether to use Redis for distributed rate limiting
            redis_url: Redis connection URL
        """
        super().__init__(app)
        self.requests = requests
        self.window = window
        self.skip_paths = set(skip_paths or [])
        self.use_redis = use_redis
        self.redis_client = None

        # Initialize storage
        if self.use_redis:
            self._init_redis(redis_url)
        else:
            # In-memory storage for development/testing
            self.requests_storage: Dict[str, list] = defaultdict(list)

    def _init_redis(self, redis_url: str) -> None:
        """Initialize Redis client for distributed rate limiting."""
        try:
            import redis.asyncio as redis

            if redis_url:
                self.redis_client = redis.from_url(redis_url)
            else:
                self.redis_client = redis.Redis(host="localhost", port=6379, db=0)

            logger.info("Redis client initialized for rate limiting")

        except ImportError:
            logger.warning(
                "Redis not available, falling back to in-memory rate limiting"
            )
            self.use_redis = False
            self.requests_storage = defaultdict(list)

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            self.use_redis = False
            self.requests_storage = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and apply rate limiting.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response from next middleware

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        # Skip rate limiting for specified paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        is_allowed, retry_after = await self._check_rate_limit(client_id)

        if not is_allowed:
            # Log rate limit violation
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "method": request.method,
                    "requests": self.requests,
                    "window": self.window,
                },
            )

            # Raise rate limit error
            raise RateLimitError(
                message=f"Rate limit exceeded. Maximum {self.requests} requests per {self.window} seconds.",
                retry_after=retry_after,
                limit=self.requests,
                window=self.window,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Window"] = str(self.window)

        current_requests, reset_time = await self._get_current_usage(client_id)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests - current_requests))
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        # Try to get user ID from authentication (if available)
        # This would need to be implemented based on your auth system
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client IP
        return request.client.host if request.client else "unknown"

    async def _check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if client is allowed to make a request.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if self.use_redis and self.redis_client:
            return await self._check_rate_limit_redis(client_id)
        else:
            return await self._check_rate_limit_memory(client_id)

    async def _check_rate_limit_redis(self, client_id: str) -> Tuple[bool, int]:
        """
        Check rate limit using Redis sliding window.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        try:
            current_time = time.time()
            window_start = current_time - self.window

            # Redis key for this client
            key = f"rate_limit:{client_id}"

            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count current requests
            current_requests = await self.redis_client.zcard(key)

            if current_requests >= self.requests:
                # Calculate retry after (when oldest request will expire)
                oldest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_request:
                    retry_after = int(oldest_request[0][1] + self.window - current_time)
                    retry_after = max(1, retry_after)
                else:
                    retry_after = self.window

                return False, retry_after

            # Add current request
            await self.redis_client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key
            await self.redis_client.expire(key, self.window)

            return True, 0

        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            # Fall back to allowing the request if Redis fails
            return True, 0

    async def _check_rate_limit_memory(self, client_id: str) -> Tuple[bool, int]:
        """
        Check rate limit using in-memory sliding window.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        window_start = current_time - self.window

        # Get client's request timestamps
        client_requests = self.requests_storage[client_id]

        # Remove old entries outside the window
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]

        # Check if limit exceeded
        if len(client_requests) >= self.requests:
            # Calculate retry after (when oldest request will expire)
            if client_requests:
                retry_after = int(client_requests[0] + self.window - current_time)
                retry_after = max(1, retry_after)
            else:
                retry_after = self.window

            return False, retry_after

        # Add current request
        client_requests.append(current_time)

        # Clean up old entries to prevent memory leaks
        self._cleanup_old_entries()

        return True, 0

    async def _get_current_usage(self, client_id: str) -> Tuple[int, int]:
        """
        Get current usage statistics for a client.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (current_requests, reset_time)
        """
        if self.use_redis and self.redis_client:
            try:
                current_time = time.time()
                window_start = current_time - self.window
                key = f"rate_limit:{client_id}"

                # Remove old entries and get count
                await self.redis_client.zremrangebyscore(key, 0, window_start)
                current_requests = await self.redis_client.zcard(key)

                # Get oldest request time to calculate reset time
                oldest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_request:
                    reset_time = int(oldest_request[0][1] + self.window)
                else:
                    reset_time = int(current_time + self.window)

                return current_requests, reset_time

            except Exception:
                return 0, int(time.time() + self.window)
        else:
            client_requests = self.requests_storage.get(client_id, [])
            current_time = time.time()
            window_start = current_time - self.window

            # Filter current requests in window
            current_requests = [req_time for req_time in client_requests if req_time > window_start]

            if current_requests:
                reset_time = int(min(current_requests) + self.window)
            else:
                reset_time = int(current_time + self.window)

            return len(current_requests), reset_time

    def _cleanup_old_entries(self) -> None:
        """Clean up old entries in memory storage to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - self.window * 2  # Keep entries for 2 windows

        # Clean up clients with old entries
        clients_to_remove = []
        for client_id, timestamps in self.requests_storage.items():
            # Filter old entries
            timestamps[:] = [t for t in timestamps if t > cutoff_time]

            # Mark empty clients for removal
            if not timestamps:
                clients_to_remove.append(client_id)

        # Remove empty clients
        for client_id in clients_to_remove:
            del self.requests_storage[client_id]