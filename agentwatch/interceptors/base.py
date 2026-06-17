"""Base streaming interceptor with safety checks"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import time
import re

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
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None
    status: TokenStatus = TokenStatus.SAFE
    status_reason: Optional[str] = None

@dataclass
class SafetyResult:
    status: TokenStatus
    reason: Optional[str] = None
    blocked_at_index: Optional[int] = None
    partial_match: Optional[str] = None
    confidence: float = 1.0

class BaseStreamInterceptor(ABC):
    def __init__(self, buffer_size: int = 1000):
        self.buffer: List[str] = []
        self.buffer_size = buffer_size
        self.total_tokens = 0
        self.is_blocked = False
        
    @abstractmethod
    async def intercept_stream(self, prompt: str, model: str = None, **kwargs) -> AsyncGenerator[TokenChunk, None]:
        pass
    
    async def process_token(self, token: str) -> SafetyResult:
        self.buffer.append(token)
        self.total_tokens += 1
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)
        return await self._safety_check()
    
    @abstractmethod
    async def _safety_check(self) -> SafetyResult:
        pass
    
    def _build_partial_command(self) -> str:
        return ''.join(self.buffer[-50:])
    
    def _detect_dangerous_patterns(self, text: str) -> Optional[str]:
        patterns = [
            r"rm\s+-rf\s+/?",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM",
            r"curl\s+.*\|\s*bash",
            r"sudo\s+",
            r"chmod\s+777",
            r"/etc/passwd",
            r"base64\s+-d",
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"subprocess\.",
            r"os\.system"
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        return None
    
    def _detect_suspicious_patterns(self, text: str) -> Optional[str]:
        patterns = [
            r"rm\s+-",
            r"DELETE\s+",
            r"DROP\s+",
            r"curl\s+",
            r"wget\s+",
            r"sudo\s+",
            r"chmod\s+"
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return pattern
        return None