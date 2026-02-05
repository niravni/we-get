"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from urllib.parse import quote_plus
from we_get.core.module import Module
import re
import requests
import socket

# Try alternative domains - some might not have Cloudflare or have weaker protection
BASE_URLS = [
    "https://1337x.to",
    "https://1337x.st", 
    "https://www.1377x.to"
]
BASE_URL = BASE_URLS[0]  # Default to first one
SEARCH_LOC = "/search/%s/1/"
LIST_LOC = "/top-100"


class leetx(object):
    """ 1337x module for we-get.
    """

    def __init__(self, pargs):
        self.links = None
        self.pargs = pargs
        self.action = None
        self.search_query = None
        self.module = Module()
        self.parse_pargs()
        self.items = dict()
        self.results = 10  # Limit the results to avoid blocking.

    def parse_pargs(self):
        for opt in self.pargs:
            if opt == "--search":
                self.action = "search"
                self.search_query = self.pargs[opt][0]
            elif opt == "--list":
                self.action = "list"

    def set_item(self, link):
        url = "%s%s" % (BASE_URL, link)
        magnet = None
        item = dict()
        
        try:
            import os
            debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
            # Use cloudscraper for 1337x to bypass Cloudflare protection
            data = self.module.http_get_request(url, debug=debug, use_cloudscraper=True)
            # Try multiple patterns for magnet links
            # Pattern 1: Standard href with magnet
            magnet_links = re.findall(r'href=[\'"]?(magnet:[^\'">]+)', data, re.IGNORECASE)
            # Pattern 2: Direct magnet links in data
            if not magnet_links:
                magnet_links = re.findall(r'(magnet:\?[^\'"\s<>]+)', data, re.IGNORECASE)
            
            # Try multiple patterns for seeders/leechers as site structure may vary
            seeders = '0'
            leechers = '0'
            
            # Pattern 1: Standard span with class="seeds"
            seeders_match = re.findall(r'<span[^>]*class=["\']seeds["\'][^>]*>(.*?)</span>', data, re.IGNORECASE | re.DOTALL)
            if not seeders_match:
                # Pattern 2: Alternative format
                seeders_match = re.findall(r'<span class=["\']seeds["\']>(.*?)</span>', data, re.IGNORECASE)
            if not seeders_match:
                # Pattern 3: Generic seeds text
                seeders_match = re.findall(r'>Seeds?[:\s]*(\d+)', data, re.IGNORECASE)
            if seeders_match:
                seeders = seeders_match[0].strip()
            
            # Pattern 1: Standard span with class="leeches"
            leechers_match = re.findall(r'<span[^>]*class=["\']leeches["\'][^>]*>(.*?)</span>', data, re.IGNORECASE | re.DOTALL)
            if not leechers_match:
                # Pattern 2: Alternative format
                leechers_match = re.findall(r'<span class=["\']leeches["\']>(.*?)</span>', data, re.IGNORECASE)
            if not leechers_match:
                # Pattern 3: Generic leechers text
                leechers_match = re.findall(r'>Leech(?:ers?)?[:\s]*(\d+)', data, re.IGNORECASE)
            if leechers_match:
                leechers = leechers_match[0].strip()
            
            # Get magnet link
            if magnet_links:
                magnet = magnet_links[0]
            
            if not magnet:
                return item
                
            try:
                name = self.module.fix_name(self.module.magnet2name(magnet))
                item.update(
                    {name: {'seeds': seeders, 'leeches': leechers, 'link': magnet}}
                )
            except (IndexError, AttributeError, ValueError) as e:
                # If magnet parsing fails, try to extract name from page title or other sources
                try:
                    # Fallback: try to get name from page
                    title_match = re.findall(r'<title[^>]*>(.*?)</title>', data, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        name = self.module.fix_name(title_match[0].split('|')[0].strip())
                        item.update(
                            {name: {'seeds': seeders, 'leeches': leechers, 'link': magnet}}
                        )
                except Exception:
                    pass
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                socket.gaierror,
                socket.error):
            pass
        except Exception:
            pass
        return item

    def search(self):
        import os
        debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        # Try multiple domains if first one fails
        for base_url in BASE_URLS:
            url = "%s%s" % (base_url, SEARCH_LOC % (quote_plus(self.search_query)))
            if debug:
                print(f"[DEBUG 1337x] Trying URL: {url}")
            try:
                # Use cloudscraper for 1337x to bypass Cloudflare protection
                data = self.module.http_get_request(url, debug=debug, use_cloudscraper=True)
                if debug:
                    print(f"[DEBUG 1337x] Received {len(data)} bytes of HTML")
                if data and len(data) > 1000:  # Got valid data
                    # Update BASE_URL for set_item calls
                    global BASE_URL
                    BASE_URL = base_url
                    break
                elif debug:
                    print(f"[DEBUG 1337x] No valid data from {base_url}, trying next domain...")
            except Exception as e:
                if debug:
                    print(f"[DEBUG 1337x] Error with {base_url}: {e}")
                continue
        
        if not data or len(data) < 1000:
            if debug:
                print("[DEBUG 1337x] No data received from any domain, returning empty results")
            return self.items
            # Try multiple patterns for finding torrent links
            # Pattern 1: Look for links in table rows (common 1337x structure)
            torrent_links = re.findall(r'<a[^>]+href=["\']([^"\']*torrent/[^"\']+)["\']', data, re.IGNORECASE)
            
            # Pattern 2: More generic torrent links
            if not torrent_links:
                torrent_links = re.findall(r'href=["\']([^"\']*torrent/[^"\']+)["\']', data, re.IGNORECASE)
            
            # Pattern 3: Any href with /torrent/ in it
            if not torrent_links:
                all_links = re.findall(r'href=["\']?([^"\'>]+)', data)
                torrent_links = [link for link in all_links if "/torrent/" in link.lower()]
            
            if debug:
                print(f"[DEBUG 1337x] Found {len(torrent_links)} torrent links")
            
            results = 0
            seen_links = set()  # Avoid duplicate processing

            for link in torrent_links:
                if results == self.results:
                    break
                # Normalize link
                if link.startswith('http'):
                    # Full URL - extract path
                    if BASE_URL in link:
                        full_link = '/' + link.split(BASE_URL)[-1].lstrip('/')
                    else:
                        continue  # External link
                elif link.startswith('/'):
                    full_link = link
                else:
                    full_link = '/' + link
                
                # Skip if we've already processed this link
                if full_link in seen_links:
                    continue
                seen_links.add(full_link)
                
                if "/torrent/" in full_link:
                    try:
                        if debug:
                            print(f"[DEBUG 1337x] Processing torrent link: {full_link}")
                        item = self.set_item(full_link)
                        if item:
                            if debug:
                                print(f"[DEBUG 1337x] Successfully extracted item: {list(item.keys())[0] if item else 'None'}")
                            self.items.update(item)
                            results += 1
                        elif debug:
                            print(f"[DEBUG 1337x] Failed to extract item from {full_link}")
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG 1337x] Error processing {full_link}: {e}")
                        # Skip this item and continue
                        continue
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                socket.gaierror,
                socket.error):
            pass
        except Exception:
            pass
        return self.items

    def list(self):
        import os
        debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        url = "%s%s" % (BASE_URL, LIST_LOC)
        try:
            # Use cloudscraper for 1337x to bypass Cloudflare protection
            data = self.module.http_get_request(url, debug=debug, use_cloudscraper=True)
            # Try multiple patterns for finding torrent links
            torrent_links = re.findall(r'href=[\'"]?([^\'">]*torrent/[^\'">]+)', data, re.IGNORECASE)
            if not torrent_links:
                links = re.findall(r'href=[\'"]?([^\'">]+)', data)
                links = [link for link in links if "/torrent/" in link]
            else:
                links = torrent_links
            
            results = 0
            seen_links = set()

            for link in links:
                if results == self.results:
                    break
                # Normalize link
                if link.startswith('/'):
                    full_link = link
                elif link.startswith('http'):
                    continue
                else:
                    full_link = '/' + link
                
                if full_link in seen_links:
                    continue
                seen_links.add(full_link)
                
                if "/torrent/" in full_link:
                    try:
                        item = self.set_item(full_link)
                        if item:
                            self.items.update(item)
                            results += 1
                    except Exception:
                        continue
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                socket.gaierror,
                socket.error):
            pass
        except Exception:
            pass
        return self.items


def main(pargs):
    run = leetx(pargs)
    if run.action == "list":
        return run.list()
    elif run.action == "search":
        return run.search()
