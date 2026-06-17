"""Factory for creating stream interceptors"""
from typing import Optional
from .base import BaseStreamInterceptor
from .openai import OpenAIStreamInterceptor
from .anthropic import AnthropicStreamInterceptor
from .google import GoogleStreamInterceptor

class StreamInterceptorFactory:
    _providers = {
        "openai": OpenAIStreamInterceptor,
        "anthropic": AnthropicStreamInterceptor,
        "google": GoogleStreamInterceptor,
        "gemini": GoogleStreamInterceptor,
    }
    
    @classmethod
    def create(cls, provider: str, api_key: str, model: Optional[str] = None, **kwargs) -> BaseStreamInterceptor:
        provider_lower = provider.lower()
        if provider_lower not in cls._providers:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {list(cls._providers.keys())}")
        interceptor_class = cls._providers[provider_lower]
        if model:
            return interceptor_class(api_key=api_key, model=model, **kwargs)
        return interceptor_class(api_key=api_key, **kwargs)