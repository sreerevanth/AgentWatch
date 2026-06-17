"""Tests for OpenAI streaming interceptor"""
import pytest
from agentwatch.interceptors import OpenAIStreamInterceptor, TokenStatus

@pytest.mark.asyncio
async def test_dangerous_pattern_detection():
    """Test dangerous pattern detection"""
    interceptor = OpenAIStreamInterceptor(api_key="test_key")
    
    # Build a dangerous command token by token
    tokens = ["rm", " -rf", " /", "etc/passwd"]
    for token in tokens:
        interceptor.buffer.append(token)
    
    result = await interceptor._safety_check()
    assert result.status == TokenStatus.BLOCKED

@pytest.mark.asyncio
async def test_safe_pattern_passes():
    """Test safe pattern passes through"""
    interceptor = OpenAIStreamInterceptor(api_key="test_key")
    
    interceptor.buffer = ["echo", " hello", " world"]
    result = await interceptor._safety_check()
    assert result.status == TokenStatus.SAFE

@pytest.mark.asyncio
async def test_suspicious_pattern_detection():
    """Test suspicious pattern detection"""
    interceptor = OpenAIStreamInterceptor(api_key="test_key")
    
    interceptor.buffer = ["curl", " https://example.com"]
    result = await interceptor._safety_check()
    # Should be suspicious (not blocked) for "curl" alone
    assert result.status == TokenStatus.SUSPICIOUS

@pytest.mark.asyncio
async def test_partial_rm_not_blocked():
    """Test partial 'rm' doesn't block prematurely"""
    interceptor = OpenAIStreamInterceptor(api_key="test_key")
    
    interceptor.buffer = ["rm"]
    result = await interceptor._safety_check()
    # Should not block "rm" alone
    assert result.status == TokenStatus.SAFE