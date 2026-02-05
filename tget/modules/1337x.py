"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from urllib.parse import quote_plus
from tget.core.module import Module
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
# 1337x search can use different formats - try multiple
SEARCH_LOCS = [
    "/search/%s/1/",  # Original format
    "/search/%s/",    # Without page number
    "/search?q=%s",   # Query parameter format
]
LIST_LOC = "/top-100"


class leetx(object):
    """ 1337x module for tget.
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
                # 1337x search URLs work better with + for spaces, or sometimes just spaces
                # We'll encode it properly in the search method
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
        data = None
        working_base_url = None
        
        try:
            # Try multiple domains if first one fails
            # 1337x search URLs: try different encodings for spaces
            # Lowercase the query first as 1337x typically uses lowercase in URLs
            search_query_lower = self.search_query.lower()
            search_formats = [
                quote_plus(search_query_lower),  # spaces -> +, lowercase
                search_query_lower.replace(' ', '+'),  # explicit + replacement, lowercase
                search_query_lower.replace(' ', '%20'),  # %20 encoding, lowercase
                search_query_lower.replace(' ', '-'),  # dash replacement, lowercase
                # Also try with original case as fallback
                quote_plus(self.search_query),  # spaces -> +, original case
                self.search_query.replace(' ', '+'),  # explicit + replacement, original case
            ]
            
            # Remove duplicates while preserving order
            seen_formats = set()
            unique_formats = []
            for fmt in search_formats:
                if fmt not in seen_formats:
                    seen_formats.add(fmt)
                    unique_formats.append(fmt)
            
            for search_encoded in unique_formats:
                if data and len(data) > 1000:
                    break  # Got valid data, stop trying formats
                
                # Try different search URL formats
                for search_loc in SEARCH_LOCS:
                    if data and len(data) > 1000:
                        break  # Got valid data, stop trying URL formats
                    
                    for base_url in BASE_URLS:
                        url = "%s%s" % (base_url, search_loc % (search_encoded))
                        if debug:
                            print(f"[DEBUG 1337x] Trying URL: {url}")
                            print(f"[DEBUG 1337x] Search query: '{self.search_query}' -> encoded: '{search_encoded}'")
                        try:
                            # Use cloudscraper for 1337x to bypass Cloudflare protection
                            test_data = self.module.http_get_request(url, debug=debug, use_cloudscraper=True)
                            if debug:
                                print(f"[DEBUG 1337x] Received {len(test_data)} bytes of HTML")
                            if test_data and len(test_data) > 1000:  # Got valid data
                                data = test_data
                                # Update BASE_URL for set_item calls
                                global BASE_URL
                                BASE_URL = base_url
                                working_base_url = base_url
                                if debug:
                                    print(f"[DEBUG 1337x] Successfully got data with encoding: '{search_encoded}' and URL format: '{search_loc}'")
                                break
                            elif debug:
                                print(f"[DEBUG 1337x] No valid data from {base_url} with encoding '{search_encoded}', trying next...")
                        except Exception as e:
                            if debug:
                                print(f"[DEBUG 1337x] Error with {base_url} and encoding '{search_encoded}': {e}")
                            continue
                    
                    if data and len(data) > 1000:
                        break  # Got valid data, stop trying other URL formats
                
                if data and len(data) > 1000:
                    break  # Got valid data, stop trying other encodings
            
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
                    if working_base_url and working_base_url in link:
                        full_link = '/' + link.split(working_base_url)[-1].lstrip('/')
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
        data = None
        working_base_url = None
        
        try:
            # Try multiple domains if first one fails
            for base_url in BASE_URLS:
                url = "%s%s" % (base_url, LIST_LOC)
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
                        working_base_url = base_url
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
            torrent_links = re.findall(r'href=[\'"]?([^\'">]*torrent/[^\'">]+)', data, re.IGNORECASE)
            if not torrent_links:
                links = re.findall(r'href=[\'"]?([^\'">]+)', data)
                links = [link for link in links if "/torrent/" in link]
            else:
                links = torrent_links
            
            if debug:
                print(f"[DEBUG 1337x] Found {len(links)} torrent links")
            
            results = 0
            seen_links = set()

            for link in links:
                if results == self.results:
                    break
                # Normalize link
                if link.startswith('http'):
                    # Full URL - extract path
                    if working_base_url and working_base_url in link:
                        full_link = '/' + link.split(working_base_url)[-1].lstrip('/')
                    else:
                        continue  # External link
                elif link.startswith('/'):
                    full_link = link
                else:
                    full_link = '/' + link
                
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
