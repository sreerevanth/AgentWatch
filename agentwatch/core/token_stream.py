"""Token stream management and buffering"""

import time
from collections import deque


class TokenStreamBuffer:
    """Manages token stream with safety checks"""

    def __init__(self, max_size: int = 1000):
        self.buffer = deque(maxlen=max_size)
        self.total_tokens = 0
        self.start_time = time.time()
        self._dangerous_detected = False
        self._blocked_at = None

    def add_token(self, token: str) -> str:
        """Add token to buffer and return full text"""
        self.buffer.append(token)
        self.total_tokens += 1
        return self.get_full_text()

    def get_full_text(self) -> str:
        """Get full text from buffer"""
        return "".join(self.buffer)

    def get_recent_text(self, n: int = 50) -> str:
        """Get last n tokens as text"""
        return "".join(list(self.buffer)[-n:])

    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
        self.total_tokens = 0

    def mark_dangerous(self, position: int):
        """Mark that dangerous content was detected"""
        self._dangerous_detected = True
        self._blocked_at = position

    @property
    def is_dangerous(self) -> bool:
        return self._dangerous_detected

    @property
    def blocked_at(self) -> int | None:
        return self._blocked_at

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def token_rate(self) -> float:
        """Tokens per second"""
        if self.elapsed_time > 0:
            return self.total_tokens / self.elapsed_time
        return 0.0
