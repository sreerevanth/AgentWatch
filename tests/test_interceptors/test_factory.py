"""Tests for stream interceptor factory"""

import pytest

from agentwatch.interceptors import StreamInterceptorFactory
from agentwatch.interceptors.anthropic import AnthropicStreamInterceptor
from agentwatch.interceptors.google import GoogleStreamInterceptor
from agentwatch.interceptors.openai import OpenAIStreamInterceptor


def test_factory_creates_openai():
    """Test factory creates OpenAI interceptor"""
    interceptor = StreamInterceptorFactory.create("openai", "test_key")
    assert isinstance(interceptor, OpenAIStreamInterceptor)


def test_factory_creates_anthropic():
    """Test factory creates Anthropic interceptor"""
    interceptor = StreamInterceptorFactory.create("anthropic", "test_key")
    assert isinstance(interceptor, AnthropicStreamInterceptor)


def test_factory_creates_google():
    """Test factory creates Google interceptor"""
    interceptor = StreamInterceptorFactory.create("google", "test_key")
    assert isinstance(interceptor, GoogleStreamInterceptor)


def test_factory_with_model_param():
    """Test factory with custom model"""
    interceptor = StreamInterceptorFactory.create("openai", "test_key", model="gpt-4-turbo")
    assert interceptor.model == "gpt-4-turbo"


def test_factory_invalid_provider():
    """Test factory with invalid provider raises error"""
    with pytest.raises(ValueError):
        StreamInterceptorFactory.create("invalid", "test_key")
