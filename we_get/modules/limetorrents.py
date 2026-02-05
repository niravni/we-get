"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from urllib.parse import quote_plus
from we_get.core.module import Module
import re

BASE_URL = "https://www.limetorrents.lol/"
SEARCH_LOC = "/search/all/%s/"
LIST_LOC = "/top100"


class limetorrents(object):
    """ limetorrents module for we-get
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
        url = url.replace(" ", "%20")
        magnet = None
        item = dict()
        try:
            data = self.module.http_get_request(url)
            links = re.findall(r'a href=[\'"]+(magnet:.*?)[\'"]+', data, re.IGNORECASE)
            seeders = '0'
            leechers = '0'
            try:
                seeders_match = re.findall(r'>Seeders : (.*?)<', data)
                if seeders_match:
                    seeders = seeders_match[0].strip()
            except (IndexError, AttributeError):
                pass
            try:
                leechers_match = re.findall(r'>Leechers : (.*?)<', data)
                if leechers_match:
                    leechers = leechers_match[0].strip()
            except (IndexError, AttributeError):
                pass

            for link in links:
                if "magnet" in link:
                    magnet = link
                    break
            if magnet is None:
                return item
            name = self.module.magnet2name(magnet)
            name = self.module.fix_name(name).strip()
            item.update(
                {name: {'seeds': seeders, 'leeches': leechers, 'link': magnet}}
            )
        except Exception:
            pass
        return item

    def search(self):
        url = "%s%s" % (BASE_URL, SEARCH_LOC % (quote_plus(self.search_query)))
        try:
            data = self.module.http_get_request(url)
            links = re.findall(r'tt-name[\'"]+>.*?</a><a href=[\'"]?([^\'">]+)', data)
            results = 0

            for link in links:
                if results == self.results:
                    break
                item = self.set_item(link)
                if item:
                    self.items.update(item)
                    results += 1
        except Exception:
            pass
        return self.items

    def list(self):
        url = "%s%s" % (BASE_URL, LIST_LOC)
        try:
            data = self.module.http_get_request(url)
            links = re.findall(r'tt-name[\'"]+><a href=[\'"]?([^\'">]+)', data)
            results = 0

            for link in links:
                if results == self.results:
                    break
                item = self.set_item(link)
                if item:
                    self.items.update(item)
                    results += 1
        except Exception:
            pass
        return self.items

def main(pargs):
    run = limetorrents(pargs)
    if run.action == "list":
        return run.list()
    elif run.action == "search":
        return run.search()
