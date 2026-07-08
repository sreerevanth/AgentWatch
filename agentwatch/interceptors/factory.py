"""Factory for creating stream interceptors"""

import logging
from typing import Optional

from .anthropic import AnthropicStreamInterceptor
from .base import BaseStreamInterceptor
from .openai import OpenAIStreamInterceptor

# Try to import Google, but make it optional
try:
    from .google import GoogleStreamInterceptor
except ImportError:
    GoogleStreamInterceptor = None
    logging.getLogger(__name__).warning(
        "Google provider requires google-generativeai package. "
        "Install with: pip install google-generativeai"
    )


class StreamInterceptorFactory:
    """Factory for creating stream interceptors"""

    _providers = {
        "openai": OpenAIStreamInterceptor,
        "anthropic": AnthropicStreamInterceptor,
    }

    # Add Google providers only if available
    if GoogleStreamInterceptor is not None:
        _providers["google"] = GoogleStreamInterceptor
        _providers["gemini"] = GoogleStreamInterceptor

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseStreamInterceptor:
        """Create a stream interceptor for the specified provider

        Args:
            provider: The provider name ('openai', 'anthropic', 'google', 'gemini')
            api_key: API key for the provider
            model: Optional model name (uses provider default if not specified)
            **kwargs: Additional arguments passed to the interceptor

        Returns:
            BaseStreamInterceptor instance

        Raises:
            ValueError: If provider is not supported or Google provider is not available
        """
        provider_lower = provider.lower()

        if provider_lower not in cls._providers:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported: {list(cls._providers.keys())}\n"
                "Note: Google providers require `google-generativeai` package."
            )

        interceptor_class = cls._providers[provider_lower]

        # Check if this is a Google provider that failed to import
        if provider_lower in ("google", "gemini") and interceptor_class is None:
            raise ValueError(
                f"Provider '{provider}' is not available. "
                "Install google-generativeai: pip install google-generativeai"
            )

        if model:
            return interceptor_class(api_key=api_key, model=model, **kwargs)
        return interceptor_class(api_key=api_key, **kwargs)

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported providers"""
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, interceptor_class: type) -> None:
        """Register a custom provider

        Args:
            name: Provider name
            interceptor_class: Interceptor class (must inherit from BaseStreamInterceptor)
        """
        if not issubclass(interceptor_class, BaseStreamInterceptor):
            raise TypeError(
                f"Interceptor class must inherit from BaseStreamInterceptor"
            )
        cls._providers[name.lower()] = interceptor_class