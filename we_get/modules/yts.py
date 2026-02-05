"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from we_get.core.module import Module
import json
import requests
import socket
from urllib.parse import quote_plus

BASE_URL = "https://yts.bz"


class yts(object):
    """ yts module using the JSON API.
    """

    def __init__(self, pargs):
        self.links = None
        self.pargs = pargs
        self.action = None
        self.quality = "720p"
        self.genre = "all"
        self.search_query = None
        self.module = Module()
        self.parse_pargs()
        self.items = dict()

    def parse_pargs(self):
        for opt in self.pargs:
            if opt == "--search":
                self.action = "search"
                # YTS API expects URL-encoded query, not dash-separated
                self.search_query = quote_plus(self.pargs[opt][0])
            elif opt == "--list":
                self.action = "list"
            elif opt == "--quality":
                self.quality = self.pargs[opt][0]
            elif opt == "--genre":
                self.genre = self.pargs[opt][0]

    def search(self):
        import os
        debug = os.environ.get('TGET_DEBUG', '').lower() in ('1', 'true', 'yes')
        # YTS API format: quality and genre need proper formatting
        quality_param = "&quality=%s" % self.quality if self.quality != "720p" else ""
        genre_param = "&genre=%s" % self.genre if self.genre != "all" else ""
        url = "%s/api/v2/list_movies.json?query_term=%s%s%s" % (
            BASE_URL,
            self.search_query,
            quality_param,
            genre_param
        )
        if debug:
            print(f"[DEBUG YTS] Search URL: {url}")
        try:
            response = self.module.http_get_request(url, debug=debug)
            if debug:
                print(f"[DEBUG YTS] Received {len(response)} bytes of JSON")
            if not response:
                if debug:
                    print("[DEBUG YTS] No data received, returning empty results")
                return self.items
            data = json.loads(response)
            if debug:
                print(f"[DEBUG YTS] JSON parsed successfully")
                print(f"[DEBUG YTS] Status: {data.get('status', 'N/A')}")
                print(f"[DEBUG YTS] Status message: {data.get('status_message', 'N/A')}")
            
            # Check if API returned an error
            if data.get('status') != 'ok' and data.get('status') != None:
                if debug:
                    print(f"[DEBUG YTS] API returned error status: {data.get('status')}")
                return self.items
            
            # Try to get movies from response
            movies = data.get('data', {}).get('movies', [])
            if not movies:
                # Sometimes movies is directly in data
                movies = data.get('movies', [])
            
            if debug:
                print(f"[DEBUG YTS] Found {len(movies)} movies in response")
            
            for movie in movies:
                if not movie:
                    continue
                torrents = movie.get('torrents', [])
                if not torrents or len(torrents) == 0:
                    if debug:
                        print(f"[DEBUG YTS] Movie '{movie.get('title', 'Unknown')}' has no torrents")
                    continue
                
                # Get base movie name
                base_name = movie.get('title', movie.get('title_english', 'Unknown'))
                year = movie.get('year', '')
                if year:
                    base_name = f"{base_name} ({year})"
                
                # Return ALL torrents for each movie (not just the first one)
                # This gives us multiple results per movie (720p, 1080p, 3D, etc.)
                for torrent in torrents:
                    if not torrent:
                        continue
                    quality = torrent.get('quality', '')
                    seeds = str(torrent.get('seeds', '0'))
                    leeches = str(torrent.get('peers', '0'))
                    link = torrent.get('url', '')
                    
                    # Build name with quality
                    if quality:
                        name = self.module.fix_name(f"{base_name} [{quality}]")
                    else:
                        name = self.module.fix_name(base_name)
                    
                    if not link:
                        # Try hash to build magnet link
                        hash_val = torrent.get('hash', '')
                        if hash_val:
                            link = f"magnet:?xt=urn:btih:{hash_val}&dn={quote_plus(name)}"
                            if debug:
                                print(f"[DEBUG YTS] Built magnet link from hash for: {name}")
                    
                    if link:
                        if debug:
                            print(f"[DEBUG YTS] Added torrent: {name} (seeds: {seeds}, leeches: {leeches})")
                        self.items.update({
                            name: {'seeds': seeds, 'leeches': leeches, 'link': link}
                        })
                    elif debug:
                        print(f"[DEBUG YTS] No link found for torrent: {name}")
        except (json.decoder.JSONDecodeError, KeyError, IndexError, TypeError):
            return self.items
        except (requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                socket.gaierror,
                socket.error):
            return self.items
        return self.items

    def list(self):
        # YTS API format: quality and genre need proper formatting
        params = []
        if self.quality != "720p":
            params.append("quality=%s" % self.quality)
        if self.genre != "all":
            params.append("genre=%s" % self.genre)
        param_string = "?" + "&".join(params) if params else ""
        url = "%s/api/v2/list_movies.json%s" % (BASE_URL, param_string)
        try:
            response = self.module.http_get_request(url)
            data = json.loads(response)
            
            # Check if API returned an error
            if data.get('status') != 'ok' and data.get('status') != None:
                return self.items
            
            # Try to get movies from response
            movies = data.get('data', {}).get('movies', [])
            if not movies:
                # Sometimes movies is directly in data
                movies = data.get('movies', [])
            
            for movie in movies:
                if not movie:
                    continue
                torrents = movie.get('torrents', [])
                if not torrents or len(torrents) == 0:
                    continue
                
                # Get base movie name
                base_name = movie.get('title', movie.get('title_english', 'Unknown'))
                year = movie.get('year', '')
                if year:
                    base_name = f"{base_name} ({year})"
                
                # Return ALL torrents for each movie (not just the first one)
                for torrent in torrents:
                    if not torrent:
                        continue
                    quality = torrent.get('quality', '')
                    seeds = str(torrent.get('seeds', '0'))
                    leeches = str(torrent.get('peers', '0'))
                    link = torrent.get('url', '')
                    
                    # Build name with quality
                    if quality:
                        torrent_name = self.module.fix_name(f"{base_name} [{quality}]")
                    else:
                        torrent_name = self.module.fix_name(base_name)
                    
                    if not link:
                        # Try hash to build magnet link
                        hash_val = torrent.get('hash', '')
                        if hash_val:
                            link = f"magnet:?xt=urn:btih:{hash_val}&dn={quote_plus(torrent_name)}"
                    if link:
                        self.items.update({torrent_name: {'leeches': leeches,
                                                          'seeds': seeds, 'link': link}})
        except (json.decoder.JSONDecodeError, KeyError, IndexError, TypeError):
            return self.items
        except (requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                socket.gaierror,
                socket.error):
            return self.items
        return self.items


def main(pargs):
    run = yts(pargs)
    if run.action == "list":
        return run.list()
    elif run.action == "search":
        return run.search()
