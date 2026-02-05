"""
Copyright (c) 2016-2022 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying.
"""

import urllib.parse
from html import unescape as html_decode
import socket

import requests

from we_get.core.utils import random_user_agent

# Fallback modern user agent if random one is too old
MODERN_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

try:
    USER_AGENT = random_user_agent()
    # If user agent is too old (contains Firefox/1 or Firefox/2), use modern one
    if "Firefox/1" in USER_AGENT or "Firefox/2" in USER_AGENT:
        USER_AGENT = MODERN_USER_AGENT
except:
    USER_AGENT = MODERN_USER_AGENT


class Module(object):
    def __init__(self):
        self.cursor = None

    def http_get_request(self, url, timeout=10):
        """http_request: create HTTP request.
        @url: URL to request
        @timeout: Request timeout in seconds (default: 10)
        @return: data.
        """
        # Use more realistic browser headers to avoid blocking
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        try:
            res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            # Check if we got blocked or got an error page
            if res.status_code != 200:
                return ""
            # Check if response is too short (likely an error page or block)
            if len(res.text) < 100:
                return ""
            # Check for common blocking/error indicators
            text_lower = res.text.lower()
            if any(indicator in text_lower for indicator in ['access denied', 'blocked', 'cloudflare', 'captcha', 'forbidden']):
                return ""
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
