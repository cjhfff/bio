"""
HTTP Client with connection pooling and retry logic
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with connection pooling and automatic retries"""
    
    def __init__(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: tuple = (5, 30)
    ):
        """
        Initialize HTTP client
        
        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor between retries
            timeout: (connect_timeout, read_timeout) in seconds
        """
        self.session = requests.Session()
        self.timeout = timeout
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        logger.info(
            f"HTTP client initialized: pool_connections={pool_connections}, "
            f"pool_maxsize={pool_maxsize}, max_retries={max_retries}"
        )
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request with configured timeout and retries"""
        timeout = kwargs.pop('timeout', self.timeout)
        return self.session.get(url, timeout=timeout, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request with configured timeout and retries"""
        timeout = kwargs.pop('timeout', self.timeout)
        return self.session.post(url, timeout=timeout, **kwargs)
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# Global HTTP client instance (singleton pattern)
_global_client: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    """Get or create the global HTTP client instance"""
    global _global_client
    if _global_client is None:
        _global_client = HTTPClient()
    return _global_client


def close_http_client():
    """Close the global HTTP client"""
    global _global_client
    if _global_client is not None:
        _global_client.close()
        _global_client = None
