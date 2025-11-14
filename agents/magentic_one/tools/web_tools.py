"""
Web browsing and extraction tools for Magentic-One

Provides async web navigation, content extraction, and search capabilities.
"""

import asyncio
import httpx
import ipaddress
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup
import json


# Simple in-memory cache to avoid repeated requests
_page_cache = {}

# Security: Blocked URL schemes to prevent SSRF
BLOCKED_SCHEMES = {'file', 'ftp', 'ftps', 'data', 'javascript', 'vbscript'}

# Security: Blocked IP ranges (private networks, localhost)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),      # Localhost
    ipaddress.ip_network('10.0.0.0/8'),       # Private
    ipaddress.ip_network('172.16.0.0/12'),    # Private
    ipaddress.ip_network('192.168.0.0/16'),   # Private
    ipaddress.ip_network('169.254.0.0/16'),   # Link-local
    ipaddress.ip_network('::1/128'),          # IPv6 localhost
    ipaddress.ip_network('fc00::/7'),         # IPv6 private
    ipaddress.ip_network('fe80::/10'),        # IPv6 link-local
]


def _validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL to prevent SSRF attacks.

    Returns:
        (is_valid, error_message) tuple
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() in BLOCKED_SCHEMES:
            return False, f"Blocked URL scheme: {parsed.scheme}"

        # Only allow http and https
        if parsed.scheme.lower() not in ('http', 'https'):
            return False, f"Only http and https schemes allowed, got: {parsed.scheme}"

        # Check for IP addresses
        hostname = parsed.hostname
        if not hostname:
            return False, "URL must have a hostname"

        # Try to parse as IP address
        try:
            ip = ipaddress.ip_address(hostname)

            # Check if IP is in blocked ranges
            for blocked_range in BLOCKED_IP_RANGES:
                if ip in blocked_range:
                    return False, f"Access to private/internal IPs is blocked: {hostname}"

        except ValueError:
            # Not an IP address, it's a domain name - that's fine
            pass

        # Block localhost variations
        if hostname.lower() in ('localhost', 'localhost.localdomain'):
            return False, "Access to localhost is blocked"

        # All checks passed
        return True, None

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


async def navigate_to_url(url: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Navigate to a URL and retrieve the page content.

    Args:
        url: The URL to visit
        use_cache: Whether to use cached content if available

    Returns:
        Dictionary with page content, status, and metadata

    Example:
        result = await navigate_to_url("https://example.com")
        if result["success"]:
            print(result["content"])
    """
    try:
        # Security: Validate URL to prevent SSRF
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return {
                "success": False,
                "error": f"URL validation failed: {error_msg}",
                "url": url
            }

        # Check cache
        if use_cache and url in _page_cache:
            return _page_cache[url]

        # Make async request
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers)

            result = {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
                "content_type": response.headers.get("content-type", ""),
                "size_bytes": len(response.content)
            }

            # Cache successful responses
            if response.status_code == 200:
                _page_cache[url] = result

            return result

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out after 30 seconds",
            "url": url
        }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error: {str(e)}",
            "url": url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": url
        }


async def search_google(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    Search Google and return results.

    Args:
        query: Search query string
        num_results: Number of results to return (max 10)

    Returns:
        Dictionary with search results

    Example:
        results = await search_google("AI agent frameworks 2024")
        for result in results["results"]:
            print(result["title"], result["url"])
    """
    try:
        # Use DuckDuckGo as it doesn't require API key and is more permissive
        # In production, you'd use Google Custom Search API
        search_url = f"https://duckduckgo.com/html/?q={query}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(search_url, headers=headers)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Search failed with status {response.status_code}",
                    "query": query
                }

            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            # DuckDuckGo result structure
            for result_div in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result_div.find('a', class_='result__a')
                snippet_elem = result_div.find('a', class_='result__snippet')

                if title_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": title_elem.get('href', ''),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {str(e)}",
            "query": query
        }


async def extract_text_content(url: str, max_length: int = 5000) -> Dict[str, Any]:
    """
    Extract main text content from a webpage.

    Args:
        url: URL to extract content from
        max_length: Maximum characters to return

    Returns:
        Dictionary with extracted text and metadata

    Example:
        content = await extract_text_content("https://example.com/article")
        print(content["text"])
    """
    try:
        # First navigate to get the page
        page_result = await navigate_to_url(url)

        if not page_result.get("success"):
            return page_result

        # Parse HTML
        soup = BeautifulSoup(page_result["content"], 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."
            truncated = True
        else:
            truncated = False

        return {
            "success": True,
            "url": url,
            "text": text,
            "length": len(text),
            "truncated": truncated,
            "title": soup.title.string if soup.title else ""
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Content extraction error: {str(e)}",
            "url": url
        }


async def extract_links(url: str, filter_pattern: str = None) -> Dict[str, Any]:
    """
    Extract all links from a webpage.

    Args:
        url: URL to extract links from
        filter_pattern: Optional regex pattern to filter links

    Returns:
        Dictionary with extracted links

    Example:
        links = await extract_links("https://news.ycombinator.com", filter_pattern="item")
    """
    try:
        page_result = await navigate_to_url(url)

        if not page_result.get("success"):
            return page_result

        soup = BeautifulSoup(page_result["content"], 'html.parser')
        links = []

        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href', '')
            text = anchor.get_text(strip=True)

            # Make absolute URL
            absolute_url = urljoin(url, href)

            # Filter if pattern provided
            if filter_pattern and not re.search(filter_pattern, absolute_url):
                continue

            links.append({
                "url": absolute_url,
                "text": text,
                "title": anchor.get('title', '')
            })

        return {
            "success": True,
            "url": url,
            "links": links,
            "count": len(links)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Link extraction error: {str(e)}",
            "url": url
        }


async def get_page_title(url: str) -> Dict[str, Any]:
    """
    Get the title of a webpage.

    Args:
        url: URL to get title from

    Returns:
        Dictionary with page title

    Example:
        title = await get_page_title("https://example.com")
    """
    try:
        page_result = await navigate_to_url(url)

        if not page_result.get("success"):
            return page_result

        soup = BeautifulSoup(page_result["content"], 'html.parser')

        title = ""
        if soup.title:
            title = soup.title.string.strip()

        # Try OpenGraph title as fallback
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()

        return {
            "success": True,
            "url": url,
            "title": title
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Title extraction error: {str(e)}",
            "url": url
        }


async def download_page(url: str, output_path: str) -> Dict[str, Any]:
    """
    Download a webpage and save to file.

    Args:
        url: URL to download
        output_path: Path to save the page

    Returns:
        Dictionary with download status

    Example:
        result = await download_page("https://example.com", "./page.html")
    """
    try:
        page_result = await navigate_to_url(url, use_cache=False)

        if not page_result.get("success"):
            return page_result

        # Save to file
        from pathlib import Path
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(page_result["content"])

        return {
            "success": True,
            "url": url,
            "output_path": str(path),
            "size_bytes": len(page_result["content"])
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Download error: {str(e)}",
            "url": url
        }


def clear_cache():
    """Clear the page cache."""
    global _page_cache
    _page_cache = {}
