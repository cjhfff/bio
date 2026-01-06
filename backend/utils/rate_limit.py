"""
Rate limiting utilities to prevent API throttling
"""
import time
import threading
from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, calls: int, period: float):
        """
        Initialize rate limiter
        
        Args:
            calls: Number of allowed calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.tokens = calls
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * (self.calls / self.period)
        self.tokens = min(self.calls, self.tokens + tokens_to_add)
        self.last_update = now
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire a token for making a call
        
        Args:
            blocking: If True, wait until a token is available
            
        Returns:
            True if token acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            if not blocking:
                return False
            
            # Calculate wait time
            wait_time = (1 - self.tokens) * (self.period / self.calls)
            
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
        
        # Wait outside the lock
        time.sleep(wait_time)
        
        with self.lock:
            self._refill_tokens()
            self.tokens -= 1
            return True
    
    def __call__(self, func: Callable) -> Callable:
        """Use rate limiter as a decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire(blocking=True)
            return func(*args, **kwargs)
        return wrapper


def rate_limit(calls: int, period: float):
    """
    Decorator for rate limiting function calls
    
    Args:
        calls: Number of allowed calls
        period: Time period in seconds
    
    Example:
        @rate_limit(calls=10, period=60)  # 10 calls per minute
        def api_call():
            pass
    """
    limiter = RateLimiter(calls, period)
    return limiter
