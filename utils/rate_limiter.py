#!/usr/bin/env python3
"""
Rate Limiter Module

Provides rate limiting for external API calls to prevent bans and ensure
fair usage of exchange APIs (Binance, Kraken, Coinbase) and Polymarket APIs.

Features:
- Per-endpoint rate limits
- Automatic backoff on 429 errors
- Request queuing
- Metrics tracking

Usage:
    from utils.rate_limiter import RateLimiter, rate_limited_request
    
    # Use decorator
    @rate_limited_request(calls=10, period=1.0)
    def get_price():
        return requests.get(url)
    
    # Or use context manager
    limiter = RateLimiter(calls=10, period=1.0)
    with limiter:
        response = requests.get(url)
"""

import time
import threading
import logging
from collections import deque
from dataclasses import dataclass, field
from functools import wraps
from typing import Dict, Optional, Callable, Any
from contextlib import contextmanager

log = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    calls: int = 10          # Number of calls allowed
    period: float = 1.0      # Time period in seconds
    burst: int = 0           # Additional burst capacity (0 = no burst)
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    max_backoff: float = 60.0    # Maximum backoff time in seconds
    retry_on_429: bool = True    # Automatically retry on rate limit errors


@dataclass
class RateLimitStats:
    """Statistics for rate limiter."""
    total_requests: int = 0
    throttled_requests: int = 0
    total_wait_time: float = 0.0
    errors_429: int = 0
    last_request_time: float = 0.0
    
    @property
    def throttle_rate(self) -> float:
        """Percentage of requests that were throttled."""
        if self.total_requests == 0:
            return 0.0
        return self.throttled_requests / self.total_requests * 100


class RateLimiter:
    """
    Token bucket rate limiter with sliding window.
    
    Thread-safe implementation that tracks request timestamps
    and enforces rate limits with automatic waiting.
    """
    
    def __init__(self, 
                 calls: int = 10, 
                 period: float = 1.0,
                 burst: int = 0,
                 name: str = "default"):
        """
        Initialize rate limiter.
        
        Args:
            calls: Number of calls allowed per period
            period: Time period in seconds
            burst: Additional burst capacity
            name: Name for logging/identification
        """
        self.calls = calls
        self.period = period
        self.burst = burst
        self.name = name
        
        self._timestamps: deque = deque()
        self._lock = threading.Lock()
        self._backoff_until: float = 0.0
        self._consecutive_429s: int = 0
        
        self.stats = RateLimitStats()
        
    def _cleanup_old_timestamps(self):
        """Remove timestamps outside the current window."""
        now = time.time()
        while self._timestamps and self._timestamps[0] < now - self.period:
            self._timestamps.popleft()
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            blocking: If True, wait until allowed. If False, return immediately.
            timeout: Maximum time to wait (None = no limit)
            
        Returns:
            True if permission granted, False if would block and blocking=False
        """
        start_time = time.time()
        
        with self._lock:
            self.stats.total_requests += 1
            
            # Check if we're in backoff period
            now = time.time()
            if now < self._backoff_until:
                wait_time = self._backoff_until - now
                if not blocking:
                    return False
                if timeout and wait_time > timeout:
                    return False
                    
                log.debug(f"[{self.name}] Backoff: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                self.stats.total_wait_time += wait_time
            
            while True:
                self._cleanup_old_timestamps()
                
                max_calls = self.calls + self.burst
                if len(self._timestamps) < max_calls:
                    # We can make the request
                    self._timestamps.append(time.time())
                    self.stats.last_request_time = time.time()
                    return True
                
                if not blocking:
                    return False
                
                # Calculate wait time
                oldest = self._timestamps[0]
                wait_time = oldest + self.period - time.time()
                
                if timeout:
                    elapsed = time.time() - start_time
                    if elapsed + wait_time > timeout:
                        return False
                
                if wait_time > 0:
                    self.stats.throttled_requests += 1
                    self.stats.total_wait_time += wait_time
                    log.debug(f"[{self.name}] Rate limited: waiting {wait_time:.3f}s")
                    time.sleep(wait_time)
    
    def report_429(self):
        """
        Report a 429 (rate limit) error from the API.
        
        This triggers exponential backoff.
        """
        with self._lock:
            self.stats.errors_429 += 1
            self._consecutive_429s += 1
            
            # Calculate backoff time
            backoff = min(
                (2 ** self._consecutive_429s) * 0.5,
                60.0  # Max 60 seconds
            )
            
            self._backoff_until = time.time() + backoff
            log.warning(f"[{self.name}] 429 error #{self._consecutive_429s}, backoff {backoff:.1f}s")
    
    def report_success(self):
        """Report a successful request (resets 429 counter)."""
        with self._lock:
            self._consecutive_429s = 0
    
    def __enter__(self):
        """Context manager entry - acquire permission."""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            'name': self.name,
            'total_requests': self.stats.total_requests,
            'throttled_requests': self.stats.throttled_requests,
            'throttle_rate': f"{self.stats.throttle_rate:.1f}%",
            'total_wait_time': f"{self.stats.total_wait_time:.2f}s",
            'errors_429': self.stats.errors_429,
        }


# Global rate limiters for different APIs
_limiters: Dict[str, RateLimiter] = {}
_limiters_lock = threading.Lock()


# Default rate limits for known APIs (requests per second)
DEFAULT_RATE_LIMITS = {
    'binance': RateLimitConfig(calls=10, period=1.0),      # 1200/min = 20/s, be conservative
    'kraken': RateLimitConfig(calls=1, period=1.0),        # Very strict
    'coinbase': RateLimitConfig(calls=10, period=1.0),     # 10/s
    'polymarket_clob': RateLimitConfig(calls=10, period=1.0),  # ~100/min = conservative
    'polymarket_data': RateLimitConfig(calls=5, period=1.0),   # Data API
    'polygon_rpc': RateLimitConfig(calls=5, period=1.0),       # Public RPC
    'default': RateLimitConfig(calls=5, period=1.0),
}


def get_limiter(name: str) -> RateLimiter:
    """
    Get or create a rate limiter for the given API.
    
    Args:
        name: API name (binance, kraken, coinbase, polymarket_clob, etc.)
        
    Returns:
        RateLimiter instance
    """
    with _limiters_lock:
        if name not in _limiters:
            config = DEFAULT_RATE_LIMITS.get(name, DEFAULT_RATE_LIMITS['default'])
            _limiters[name] = RateLimiter(
                calls=config.calls,
                period=config.period,
                burst=config.burst,
                name=name
            )
        return _limiters[name]


def rate_limited_request(
    api: str = 'default',
    calls: Optional[int] = None,
    period: Optional[float] = None
):
    """
    Decorator to rate limit a function.
    
    Args:
        api: API name for rate limit lookup
        calls: Override calls per period (uses default if None)
        period: Override period in seconds (uses default if None)
        
    Usage:
        @rate_limited_request(api='binance')
        def get_binance_price(symbol):
            return requests.get(f"https://api.binance.com/...?symbol={symbol}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_limiter(api)
            
            # Override config if specified
            if calls is not None:
                limiter.calls = calls
            if period is not None:
                limiter.period = period
            
            with limiter:
                try:
                    result = func(*args, **kwargs)
                    
                    # Check for 429 response
                    if hasattr(result, 'status_code') and result.status_code == 429:
                        limiter.report_429()
                    else:
                        limiter.report_success()
                    
                    return result
                except Exception as e:
                    if '429' in str(e) or 'rate' in str(e).lower():
                        limiter.report_429()
                    raise
        
        return wrapper
    return decorator


@contextmanager
def rate_limit(api: str = 'default'):
    """
    Context manager for rate limiting.
    
    Usage:
        with rate_limit('binance'):
            response = requests.get(url)
    """
    limiter = get_limiter(api)
    with limiter:
        yield limiter


def get_all_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all rate limiters."""
    with _limiters_lock:
        return {name: limiter.get_stats() for name, limiter in _limiters.items()}


def reset_all():
    """Reset all rate limiters (useful for testing)."""
    global _limiters
    with _limiters_lock:
        _limiters.clear()


class RateLimitedSession:
    """
    Requests session with built-in rate limiting.
    
    Usage:
        session = RateLimitedSession()
        
        # Automatically rate-limited
        response = session.get('binance', 'https://api.binance.com/...')
    """
    
    def __init__(self):
        import requests
        self._session = requests.Session()
        
    def _detect_api(self, url: str) -> str:
        """Detect API from URL."""
        url_lower = url.lower()
        
        if 'binance.com' in url_lower:
            return 'binance'
        elif 'kraken.com' in url_lower:
            return 'kraken'
        elif 'coinbase.com' in url_lower:
            return 'coinbase'
        elif 'polymarket.com' in url_lower:
            if 'clob' in url_lower:
                return 'polymarket_clob'
            return 'polymarket_data'
        elif 'polygon-rpc.com' in url_lower:
            return 'polygon_rpc'
        
        return 'default'
    
    def request(self, method: str, url: str, api: Optional[str] = None, **kwargs):
        """
        Make a rate-limited request.
        
        Args:
            method: HTTP method
            url: Request URL
            api: API name (auto-detected if None)
            **kwargs: Passed to requests
        """
        if api is None:
            api = self._detect_api(url)
        
        with rate_limit(api):
            response = self._session.request(method, url, **kwargs)
            
            if response.status_code == 429:
                get_limiter(api).report_429()
            else:
                get_limiter(api).report_success()
            
            return response
    
    def get(self, url: str, api: Optional[str] = None, **kwargs):
        """Rate-limited GET request."""
        return self.request('GET', url, api, **kwargs)
    
    def post(self, url: str, api: Optional[str] = None, **kwargs):
        """Rate-limited POST request."""
        return self.request('POST', url, api, **kwargs)


if __name__ == '__main__':
    # Self-test
    print("Rate Limiter self-test")
    print("-" * 40)
    
    # Test basic rate limiting
    limiter = RateLimiter(calls=3, period=1.0, name='test')
    
    print("Making 5 rapid requests (limit: 3/s)...")
    start = time.time()
    
    for i in range(5):
        with limiter:
            elapsed = time.time() - start
            print(f"  Request {i+1} at {elapsed:.3f}s")
    
    print(f"\nStats: {limiter.get_stats()}")
    
    # Test decorator
    @rate_limited_request(api='test', calls=2, period=0.5)
    def test_func(n):
        return f"Result {n}"
    
    print("\nTesting decorator (2 calls/0.5s)...")
    start = time.time()
    for i in range(4):
        result = test_func(i)
        elapsed = time.time() - start
        print(f"  {result} at {elapsed:.3f}s")
