"""Tests for rate limiting middleware and functionality."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from agentwatch.api.middleware.rate_limiter import RateLimitMiddleware, RateLimiter


class TestRateLimiter:
    """Test the RateLimiter class."""

    def test_initialization(self):
        """Test RateLimiter initializes with correct defaults."""
        limiter = RateLimiter()
        assert limiter.user_limit == 100
        assert limiter.global_limit == 10000
        assert limiter.window_sec == 3600

    def test_per_user_rate_limiting(self):
        """Test per-user rate limiting enforcement."""
        limiter = RateLimiter(user_limit=3, window_sec=3600)

        for i in range(3):
            allowed, quota = limiter.check_rate_limit("user1")
            assert allowed is True

        allowed, quota = limiter.check_rate_limit("user1")
        assert allowed is False

    def test_global_rate_limiting(self):
        """Test global rate limiting enforcement."""
        limiter = RateLimiter(user_limit=10, global_limit=5, window_sec=3600)

        for i in range(5):
            user_id = f"user{i}"
            allowed, quota = limiter.check_rate_limit(user_id)
            assert allowed is True

        allowed, quota = limiter.check_rate_limit("user99")
        assert allowed is False


class TestRateLimitMiddleware:
    """Test the RateLimitMiddleware integration."""

    @pytest.fixture
    def app_with_limiter(self):
        """Create a FastAPI app with rate limiting middleware for testing."""
        app = FastAPI()
        limiter = RateLimiter(user_limit=3, global_limit=10, window_sec=3600)
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        return app

    def test_successful_request_includes_headers(self, app_with_limiter):
        """Test that successful requests include rate limit headers."""
        client = TestClient(app_with_limiter)
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-RateLimit-User-Limit" in response.headers

    def test_rate_limit_exceeded_returns_429(self, app_with_limiter):
        """Test that exceeding rate limit returns 429."""
        client = TestClient(app_with_limiter)

        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
