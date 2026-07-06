"""
Legacy compatibility wrapper for ModelRouter.
Please use agentwatch.infrastructure.router instead.
"""

from agentwatch.infrastructure.router import CircuitState, ModelRouter, ProviderHealth

__all__ = ["ModelRouter", "ProviderHealth", "CircuitState"]
