"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from we_get.core.module import Module
import re
import requests
import socket

BASE_URL = "https://eztv.re"
SEARCH_LOC = "/search/%s/"
LIST_LOC = "/"


class eztv(object):
    """ eztv module for we-get.
    """

    def __init__(self, pargs):
        self.links = None
        self.pargs = pargs
        self.action = None
        self.search_query = None
        self.module = Module()
        self.parse_pargs()
        self.items = dict()

    def parse_pargs(self):
        for opt in self.pargs:
            if opt == "--search":
                self.action = "search"
                self.search_query = self.pargs[opt][0].replace(' ', '-')
            elif opt == "--list":
                self.action = "list"

    def _parse_data(self, data):
        import os
        debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        
        if debug:
            print(f"[DEBUG EZTV] Starting to parse {len(data)} bytes of HTML")
        
        # Clean up data
        data = data.replace('\t', '').replace('\n', '')
        
        # Try multiple patterns for finding torrent rows
        # Pattern 1: Original pattern
        items = re.findall(
            r'<tr[^>]*name=["\']hover["\'][^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
            data,
            re.IGNORECASE | re.DOTALL
        )
        
        if debug:
            print(f"[DEBUG EZTV] Pattern 1 found {len(items)} items")
        
        # Pattern 2: Alternative row patterns
        if not items:
            items = re.findall(
                r'<tr[^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
                data,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 2 found {len(items)} items")
        
        # Pattern 3: Generic table rows with magnet links
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?magnet:.*?)</tr>',
                data,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 3 found {len(items)} items")
        
        # Pattern 4: Look for any table rows
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?)</tr>',
                data,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 4 (any table row) found {len(items)} items")
        
        # Always check for magnet links directly in the HTML (Pattern 5)
        # This is important because magnet links might not be in table rows
        magnet_links = re.findall(r'(magnet:\?[^\'"\s<>]+)', data, re.IGNORECASE)
        if debug:
            print(f"[DEBUG EZTV] Pattern 5 (direct magnet links) found {len(magnet_links)} magnet links in HTML")
        
        # If we found magnet links but no items from table rows, use magnet links directly
        if magnet_links and not items:
            items = [f"magnet_link:{link}" for link in magnet_links[:50]]  # Limit to 50
            if debug:
                print(f"[DEBUG EZTV] Using direct magnet links as items")
        # If we have both table rows and magnet links, add magnet links to items
        elif magnet_links and items:
            # Add magnet links as items
            items.extend([f"magnet_link:{link}" for link in magnet_links[:50]])
            if debug:
                print(f"[DEBUG EZTV] Added {len(magnet_links)} direct magnet links to items")
        
        if debug:
            print(f"[DEBUG EZTV] Total items to process: {len(items)}")
            if items and len(items) > 0:
                # Show sample of first item to understand structure
                sample_item = items[0]
                if not sample_item.startswith("magnet_link:"):
                    print(f"[DEBUG EZTV] Sample item (first 300 chars): {sample_item[:300]}")
        
        items_with_magnet = 0
        for item in items:
            # Handle dummy items from Pattern 5
            if item.startswith("magnet_link:"):
                magnet = item.replace("magnet_link:", "")
                try:
                    name = self.module.fix_name(self.module.magnet2name(magnet))
                    self.items.update({
                        name: {'seeds': '0', 'leeches': '?', 'link': magnet}
                    })
                    items_with_magnet += 1
                    if debug:
                        print(f"[DEBUG EZTV] Added item from direct magnet: {name[:50]}...")
                except Exception as e:
                    if debug:
                        print(f"[DEBUG EZTV] Failed to parse magnet link: {e}")
                continue
            
            if "magnet:" not in item:
                continue
            
            items_with_magnet += 1
            if debug and items_with_magnet <= 3:
                print(f"[DEBUG EZTV] Processing item {items_with_magnet} (first 200 chars): {item[:200]}")
                
            try:
                # Try to find seeds - multiple patterns
                seeds = '0'
                seeds_match = re.findall(
                    r'<font[^>]*color=["\']green["\'][^>]*>(.*?)</font>',
                    item,
                    re.IGNORECASE
                )
                if not seeds_match:
                    # Alternative: look for seed count in text
                    seeds_match = re.findall(r'>Seeds?[:\s]*(\d+(?:[,\s]\d+)*)', item, re.IGNORECASE)
                if seeds_match:
                    seeds = seeds_match[0].replace(',', '').replace(' ', '')
                
                # EZTV typically doesn't return leechers
                leeches = "?"
                
                # Find magnet link - try multiple patterns
                magnet = None
                magnet_matches = re.findall(r'href=[\'"]?(magnet:[^\'">]+)', item, re.IGNORECASE)
                if not magnet_matches:
                    # Alternative: direct magnet link
                    magnet_matches = re.findall(r'(magnet:\?[^\'"\s<>]+)', item, re.IGNORECASE)
                
                if magnet_matches:
                    magnet = magnet_matches[0]
                else:
                    # Fallback: try to get from all href links
                    all_links = re.findall(r'href=[\'"]?([^\'">]+)', item)
                    for link in all_links:
                        if 'magnet:' in link:
                            magnet = link
                            break
                
                if not magnet:
                    continue
                
                try:
                    name = self.module.fix_name(self.module.magnet2name(magnet))
                    self.items.update({
                        name: {'seeds': seeds, 'leeches': leeches, 'link': magnet}
                    })
                    if debug:
                        print(f"[DEBUG EZTV] Successfully added item: {name[:50]}...")
                except (IndexError, AttributeError, ValueError) as e:
                    if debug:
                        print(f"[DEBUG EZTV] Magnet parsing failed, trying title extraction: {e}")
                    # If parsing fails, try to extract name from item text
                    try:
                        title_match = re.findall(r'<a[^>]*>(.*?)</a>', item, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            name = self.module.fix_name(title_match[0].strip())
                            self.items.update({
                                name: {'seeds': seeds, 'leeches': leeches, 'link': magnet}
                            })
                            if debug:
                                print(f"[DEBUG EZTV] Added item from title: {name[:50]}...")
                    except Exception as e2:
                        if debug:
                            print(f"[DEBUG EZTV] Title extraction also failed: {e2}")
                        pass
            except Exception as e:
                if debug:
                    print(f"[DEBUG EZTV] Error processing item: {e}")
                # Skip this item and continue
                continue
        
        if debug:
            print(f"[DEBUG EZTV] Items with magnet links found: {items_with_magnet}")
            print(f"[DEBUG EZTV] Total items added: {len(self.items)}")

    def search(self):
        import os
        debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        url = "%s%s" % (BASE_URL, SEARCH_LOC % (self.search_query))
        if debug:
            print(f"[DEBUG EZTV] Search URL: {url}")
        try:
            data = self.module.http_get_request(url, timeout=10, debug=debug)
            if debug:
                print(f"[DEBUG EZTV] Received {len(data)} bytes of data")
            if not data:
                if debug:
                    print("[DEBUG EZTV] No data received")
                return self.items
            self._parse_data(data)
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
        url = "%s%s" % (BASE_URL, LIST_LOC)
        try:
            data = self.module.http_get_request(url, timeout=10)
            self._parse_data(data)
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
    run = eztv(pargs)
    if run.action == "list":
        return run.list()
    elif run.action == "search":
        return run.search()
