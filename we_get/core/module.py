"""
Copyright (c) 2016-2022 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying.
"""

import urllib.parse
from html import unescape as html_decode
import socket

import requests

# Try to import cloudscraper for Cloudflare bypass (optional)
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

from we_get.core.utils import random_user_agent

# Modern user agents - always use these instead of old ones from the file
MODERN_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Always use modern user agent - the old ones in useragents.txt are too outdated
from random import choice
USER_AGENT = choice(MODERN_USER_AGENTS)


class Module(object):
    def __init__(self):
        self.cursor = None

    def http_get_request(self, url, timeout=10, debug=False, use_cloudscraper=False):
        """http_request: create HTTP request.
        @url: URL to request
        @timeout: Request timeout in seconds (default: 10)
        @debug: Enable debug output
        @use_cloudscraper: Use cloudscraper to bypass Cloudflare (if available)
        @return: data.
        """
        import os
        debug = debug or os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        # Use cloudscraper if requested and available (for Cloudflare protection)
        res = None
        if use_cloudscraper and HAS_CLOUDSCRAPER:
            if debug:
                print(f"[DEBUG] Using cloudscraper to bypass Cloudflare")
            # Try different cloudscraper configurations
            try:
                # First try: default cloudscraper
                scraper = cloudscraper.create_scraper()
                if debug:
                    print(f"[DEBUG] Requesting URL: {url}")
                res = scraper.get(url, timeout=timeout, allow_redirects=True)
                # If we got a challenge page, try with browser-like settings
                if res.status_code == 403 and 'just a moment' in res.text.lower():
                    if debug:
                        print(f"[DEBUG] Got Cloudflare challenge, trying with browser emulation")
                    import time
                    time.sleep(2)  # Small delay
                    # Try with a browser-like scraper
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'windows',
                            'desktop': True
                        }
                    )
                    res = scraper.get(url, timeout=timeout + 5, allow_redirects=True)
            except Exception as err:
                if debug:
                    print(f"[DEBUG] cloudscraper failed, falling back to requests: {err}")
                res = None  # Force fallback to requests
        
        # Use regular requests if cloudscraper not used, not available, or failed
        if res is None:
            # Use more realistic browser headers to avoid blocking
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.google.com/",
                "DNT": "1"
            }
            if debug:
                print(f"[DEBUG] Requesting URL: {url}")
                print(f"[DEBUG] User-Agent: {USER_AGENT[:50]}...")
            res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        # Process response (works for both cloudscraper and requests)
        try:
            if debug:
                print(f"[DEBUG] Status Code: {res.status_code}")
                print(f"[DEBUG] Response Length: {len(res.content)} bytes (raw), {len(res.text)} bytes (decoded)")
                print(f"[DEBUG] Final URL (after redirects): {res.url}")
                print(f"[DEBUG] Content-Type: {res.headers.get('Content-Type', 'N/A')}")
                print(f"[DEBUG] Content-Encoding: {res.headers.get('Content-Encoding', 'N/A')}")
                if 'cf-ray' in res.headers:
                    print(f"[DEBUG] Cloudflare detected (CF-Ray: {res.headers.get('cf-ray')})")
            
            # Check if we got blocked or got an error page
            if res.status_code == 403:
                if debug:
                    print(f"[DEBUG] 403 Forbidden - Site is blocking the request")
                    # Check if it's a Cloudflare challenge
                    response_lower = res.text.lower() if res.text else ""
                    if 'just a moment' in response_lower or 'checking your browser' in response_lower:
                        print(f"[DEBUG] Cloudflare JavaScript challenge detected - cloudscraper cannot bypass this level of protection")
                        print(f"[DEBUG] This site requires a real browser with JavaScript execution")
                    elif 'cloudflare' in response_lower or 'cf-ray' in res.headers or 'challenge' in response_lower:
                        print(f"[DEBUG] Cloudflare protection detected")
                    # Show first 500 chars of decoded text
                    try:
                        if res.text and len(res.text) > 0:
                            preview = res.text[:500]
                            print(f"[DEBUG] Response preview (text): {preview}")
                        else:
                            print(f"[DEBUG] Response is binary/compressed, cannot preview as text")
                            print(f"[DEBUG] First 100 bytes (hex): {res.content[:100].hex()}")
                    except Exception as e:
                        print(f"[DEBUG] Error reading response: {e}")
                return ""
            # Also check for challenge pages even with 200 status
            elif res.status_code == 200:
                response_lower = res.text.lower() if res.text else ""
                if 'just a moment' in response_lower or 'checking your browser' in response_lower:
                    if debug:
                        print(f"[DEBUG] Got 200 but response is a Cloudflare challenge page")
                    return ""
            elif res.status_code != 200:
                if debug:
                    print(f"[DEBUG] Non-200 status code: {res.status_code}")
                return ""
            # Check if response is too short (likely an error page or block)
            if len(res.text) < 100:
                if debug:
                    print(f"[DEBUG] Response too short ({len(res.text)} bytes), likely error page")
                return ""
            # Check for common blocking/error indicators
            text_lower = res.text.lower()
            blocking_indicators = ['access denied', 'blocked', 'cloudflare', 'captcha', 'forbidden']
            found_indicators = [ind for ind in blocking_indicators if ind in text_lower]
            if found_indicators:
                if debug:
                    print(f"[DEBUG] Blocking indicators found: {found_indicators}")
                return ""
            if debug:
                print(f"[DEBUG] Successfully received {len(res.text)} bytes of data")
            return res.text
        except requests.exceptions.Timeout:
            print("Error: Timeout when opening following url: {}".format(url))
            raise
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.RequestException,
                socket.gaierror,
                socket.error) as err:
            print("Error: Network error when opening following url: {} - {}".format(url, err))
            raise
        except Exception as err:
            print("Error when opening following url: {}.\n{}".format(err, url))
            raise err

    def http_custom_get_request(self, url, headers, timeout=10):
        """http_custom_get_request: HTTP GET request with custom headers.
        @url: URL to request
        @headers: Custom headers dictionary
        @timeout: Request timeout in seconds (default: 10)
        @return: data.
        """
        try:
            return requests.get(url, headers=headers, timeout=timeout).text
        except requests.exceptions.Timeout:
            print("Error: Timeout when opening following url: {}".format(url))
            raise
        except (requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                socket.gaierror,
                socket.error) as err:
            print("Error: Network error when opening following url: {} - {}".format(url, err))
            raise
        except Exception as err:
            print("Error when opening following url: {}.\n{}".format(err, url))
            raise

    def magnet2name(self, link):
        """magnet2name: return torrent name from magnet link.
        @magnet - link.
        """
        return link.split("&")[1].split("dn=")[1]

    def fix_name(self, name):
        """fix_name: fix the torrent_name (Hello%20%20Worl+d to Hello_World)."""
        name = html_decode(name)
        return urllib.parse.unquote(
            name.replace("+", ".")
            .replace("[", "")
            .replace("]", "")
            .replace(" ", ".")
            .replace("'", "")
        )
