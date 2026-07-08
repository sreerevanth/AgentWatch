"""Base streaming interceptor with safety checks"""

import re
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum


class TokenStatus(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class TokenChunk:
    content: str
    index: int
    timestamp: float = field(default_factory=time.time)
    is_tool_call: bool = False
    tool_name: str | None = None
    tool_args: str | None = None
    status: TokenStatus = TokenStatus.SAFE
    status_reason: str | None = None


@dataclass
class SafetyResult:
    status: TokenStatus
    reason: str | None = None
    blocked_at_index: int | None = None
    partial_match: str | None = None
    confidence: float = 1.0


class BaseStreamInterceptor(ABC):
    """Abstract base for all streaming interceptors"""
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.reset_state()

    def reset_state(self) -> None:
        """Reset interceptor state for a new stream"""
        self.buffer: list[str] = []
        self.total_tokens = 0
        self.is_blocked = False

    @abstractmethod
    async def intercept_stream(
        self, prompt: str, model: str | None = None, **kwargs
    ) -> AsyncGenerator[TokenChunk, None]:
        """Intercept and process token stream"""
        pass

    async def process_token(self, token: str) -> SafetyResult:
        """Process a single token incrementally"""
        self.buffer.append(token)
        self.total_tokens += 1
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)
        return await self._safety_check()

    @abstractmethod
    async def _safety_check(self) -> SafetyResult:
        """Implement safety logic per provider"""
        pass

    def _build_partial_command(self) -> str:
        """Build partial command from recent tokens"""
        return "".join(self.buffer[-50:])

    def _detect_dangerous_patterns(self, text: str) -> str | None:
        """Check for dangerous patterns incrementally"""
        patterns = [
            r"rm\s+-rf\s+/?",
            r"rm\s+-r\s+-f\s+/?",
            r"rm\s+--recursive\s+--force\s+/?",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM\s+\w+\s+WHERE\s+1=1",
            r"curl\s+.*\s*\|\s*(?:bash|sh)",
            r"wget\s+.*\s*\|\s*(?:bash|sh)",
            r"sudo\s+.*",
            r"chmod\s+777\s+/?",
            r"chmod\s+0777\s+/?",
            r"/etc/passwd",
            r"base64\s+-d",
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"subprocess\.",
            r"os\.system",
            r"dd\s+of=/dev/",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        return None

    def _detect_suspicious_patterns(self, text: str) -> str | None:
        """Check for suspicious patterns (partial matches)"""
        patterns = [
            r"rm\s+-",
            r"DELETE\s+",
            r"DROP\s+",
            r"curl\s+",
            r"wget\s+",
            r"sudo\s+",
            r"chmod\s+",
            r"chown\s+",
            r"kill\s+",
            r"pkill\s+",
            r"systemctl\s+stop",
            r"service\s+.*\s+stop",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        return None