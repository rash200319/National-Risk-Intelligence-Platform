"""
Resilience utilities for robust data fetching with retry logic and exponential backoff.
"""
import logging
import random
import requests
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

USER_AGENT_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]

DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT_POOL[0],
    'Accept': 'application/rss+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}


def build_request_headers(extra_headers=None):
    headers = DEFAULT_HEADERS.copy()
    headers['User-Agent'] = random.choice(USER_AGENT_POOL)
    if extra_headers:
        headers.update(extra_headers)
    return headers


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
    headers = build_request_headers(headers)
    
    response = requests.get(url, headers=headers, timeout=10, **kwargs)
    response.raise_for_status()
    return response


@resilient_fetch(max_retries=2)
def fetch_rss_with_retry(url: str, headers=None, **kwargs):
    """Fetch RSS feed URL with retry logic."""
    headers = build_request_headers(headers)
    response = requests.get(url, headers=headers, timeout=10, **kwargs)
    response.raise_for_status()
    return response
