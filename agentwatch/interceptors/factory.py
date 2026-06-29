"""Factory for creating stream interceptors"""

from .anthropic import AnthropicStreamInterceptor
from .base import BaseStreamInterceptor
from .google import GoogleStreamInterceptor
from .openai import OpenAIStreamInterceptor


class StreamInterceptorFactory:
    _providers = {
        "openai": OpenAIStreamInterceptor,
        "anthropic": AnthropicStreamInterceptor,
        "google": GoogleStreamInterceptor,
        "gemini": GoogleStreamInterceptor,
    }

    @classmethod
    def create(
        cls, provider: str, api_key: str, model: str | None = None, **kwargs
    ) -> BaseStreamInterceptor:
        provider_lower = provider.lower()
        if provider_lower not in cls._providers:
            raise ValueError(
                f"Unsupported provider: {provider}. Supported: {list(cls._providers.keys())}"
            )
        interceptor_class = cls._providers[provider_lower]
        if model:
            return interceptor_class(api_key=api_key, model=model, **kwargs)
        return interceptor_class(api_key=api_key, **kwargs)
