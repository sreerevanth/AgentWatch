"""AgentWatch — Reliability, Safety, and Observability for AI Agents."""

__version__ = "0.2.0"

# Core
from agentwatch.core.watcher import (
    AgentWatchBlockedError,
    GenericAdapter,
    detect_framework,
    detect_framework_label,
    watch,
)

# Interceptors (Streaming)
try:
    from agentwatch.interceptors import (
        BaseStreamInterceptor,
        OpenAIStreamInterceptor,
        AnthropicStreamInterceptor,
        StreamInterceptorFactory,
        TokenChunk,
        TokenStatus,
        SafetyResult,
    )
except ImportError:
    # Streaming interceptors may not be fully set up yet
    BaseStreamInterceptor = None
    OpenAIStreamInterceptor = None
    AnthropicStreamInterceptor = None
    StreamInterceptorFactory = None
    TokenChunk = None
    TokenStatus = None
    SafetyResult = None

# Google is optional
try:
    from agentwatch.interceptors import GoogleStreamInterceptor
except ImportError:
    GoogleStreamInterceptor = None

# Auditors (BFT Multi-Auditor)
try:
    from agentwatch.auditors import (
        BFTAuditor,
        BaseAuditor,
        AuditResult,
        ConsensusEngine,
        ConsensusResult,
        ConsensusAlgorithm,
        TrustScorer,
        TrustScore,
        OpenAIAuditor,
        AnthropicAuditor,
        GoogleAuditor,
    )
except ImportError:
    BFTAuditor = None
    BaseAuditor = None
    AuditResult = None
    ConsensusEngine = None
    ConsensusResult = None
    ConsensusAlgorithm = None
    TrustScorer = None
    TrustScore = None
    OpenAIAuditor = None
    AnthropicAuditor = None
    GoogleAuditor = None

# WebSocket
try:
    from agentwatch.api.websocket_stream import stream_ws_manager, StreamWebSocketManager
except ImportError:
    stream_ws_manager = None
    StreamWebSocketManager = None

# Token Stream
try:
    from agentwatch.core.token_stream import TokenStreamBuffer
except ImportError:
    TokenStreamBuffer = None

__all__ = [
    # Version
    "__version__",
    
    # Core
    "watch",
    "detect_framework",
    "detect_framework_label",
    "GenericAdapter",
    "AgentWatchBlockedError",
    
    # Streaming Interceptors
    "BaseStreamInterceptor",
    "OpenAIStreamInterceptor",
    "AnthropicStreamInterceptor",
    "GoogleStreamInterceptor",
    "StreamInterceptorFactory",
    "TokenChunk",
    "TokenStatus",
    "SafetyResult",
    
    # BFT Multi-Auditor
    "BFTAuditor",
    "BaseAuditor",
    "AuditResult",
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusAlgorithm",
    "TrustScorer",
    "TrustScore",
    "OpenAIAuditor",
    "AnthropicAuditor",
    "GoogleAuditor",
    
    # WebSocket
    "stream_ws_manager",
    "StreamWebSocketManager",
    
    # Token Stream
    "TokenStreamBuffer",
]

# Remove None values from __all__
__all__ = [item for item in __all__ if item is not None]