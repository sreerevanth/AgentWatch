"""Rate Limiting Middleware"""
import time
from collections import defaultdict

class RateLimiter:
    """Per-user and global rate limiting."""
    
    def __init__(self, user_limit: int = 100, window_sec: int = 3600):
        self.user_limit = user_limit
        self.window_sec = window_sec
        self.user_buckets = defaultdict(lambda: {"count": 0, "start": time.time()})
        self.global_bucket = {"count": 0, "start": time.time()}
    
    def check_rate_limit(self, user_id: str):
        """Check if user has exceeded rate limit."""
        now = time.time()
        bucket = self.user_buckets[user_id]
        
        if now - bucket["start"] > self.window_sec:
            bucket["count"] = 0
            bucket["start"] = now
        
        bucket["count"] += 1
        return bucket["count"] <= self.user_limit
