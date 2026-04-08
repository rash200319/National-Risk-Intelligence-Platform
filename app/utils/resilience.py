"""
Resilience utilities for robust data fetching with retry logic and exponential backoff.
"""
import logging
import requests
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}


def resilient_fetch(max_retries=3, backoff_factor=2, timeout=10):
    """
    Decorator for resilient HTTP requests with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        timeout: Request timeout in seconds
    """
    return retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(max_retries),
        retry=retry_if_exception_type((
            requests.ConnectionError,
            requests.Timeout,
            requests.RequestException
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


@resilient_fetch(max_retries=3)
def fetch_url(url: str, headers=None, **kwargs):
    """
    Fetch URL with automatic retry on failure.
    
    Args:
        url: URL to fetch
        headers: HTTP headers
        **kwargs: Additional arguments to pass to requests.get
    
    Returns:
        requests.Response object
    """
    if headers is None:
        headers = DEFAULT_HEADERS.copy()
    else:
        merged_headers = DEFAULT_HEADERS.copy()
        merged_headers.update(headers)
        headers = merged_headers
    
    response = requests.get(url, headers=headers, timeout=10, **kwargs)
    response.raise_for_status()
    return response


@resilient_fetch(max_retries=2)
def fetch_rss_with_retry(url: str, **kwargs):
    """Fetch RSS feed URL with retry logic."""
    headers = DEFAULT_HEADERS.copy()
    response = requests.get(url, headers=headers, timeout=10, **kwargs)
    response.raise_for_status()
    return response
