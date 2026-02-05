"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from we_get.core.module import Module
import re
import requests
import socket

BASE_URL = "https://eztvx.to"
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
        # Clean up data
        data = data.replace('\t', '').replace('\n', '')
        
        # Try multiple patterns for finding torrent rows
        # Pattern 1: Original pattern
        items = re.findall(
            r'<tr[^>]*name=["\']hover["\'][^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
            data,
            re.IGNORECASE | re.DOTALL
        )
        
        # Pattern 2: Alternative row patterns
        if not items:
            items = re.findall(
                r'<tr[^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
                data,
                re.IGNORECASE | re.DOTALL
            )
        
        # Pattern 3: Generic table rows with magnet links
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?magnet:.*?)</tr>',
                data,
                re.IGNORECASE | re.DOTALL
            )

        for item in items:
            if "magnet:" not in item:
                continue
                
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
                except (IndexError, AttributeError, ValueError):
                    # If parsing fails, try to extract name from item text
                    try:
                        title_match = re.findall(r'<a[^>]*>(.*?)</a>', item, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            name = self.module.fix_name(title_match[0].strip())
                            self.items.update({
                                name: {'seeds': seeds, 'leeches': leeches, 'link': magnet}
                            })
                    except Exception:
                        pass
            except Exception:
                # Skip this item and continue
                continue

    def search(self):
        url = "%s%s" % (BASE_URL, SEARCH_LOC % (self.search_query))
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
