"""AgentWatch — Reliability, Safety, and Observability for AI Agents."""

__version__ = "0.2.0"

from agentwatch.core.watcher import (  # noqa: E402
    GenericAdapter,
    detect_framework,
    detect_framework_label,
    watch,
)

__all__ = [
    "__version__",
    "watch",
    "detect_framework",
    "detect_framework_label",
    "GenericAdapter",
]
