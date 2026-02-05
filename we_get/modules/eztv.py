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
        
        # Search for magnet links in original data first (before cleaning)
        # Try multiple patterns for magnet links
        magnet_links = []
        # Pattern A: Standard magnet:?xt=...
        magnet_links.extend(re.findall(r'magnet:\?[^\'"\s<>"]+', data, re.IGNORECASE))
        # Pattern B: magnet: with any characters (more flexible)
        if not magnet_links:
            magnet_links.extend(re.findall(r'magnet:[^\'"\s<>"]{20,}', data, re.IGNORECASE))
        # Pattern C: Look for href with magnet
        href_magnets = re.findall(r'href=["\']?(magnet:[^"\'>\s]+)', data, re.IGNORECASE)
        if href_magnets:
            magnet_links.extend(href_magnets)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_magnet_links = []
        for link in magnet_links:
            if link not in seen:
                seen.add(link)
                unique_magnet_links.append(link)
        magnet_links = unique_magnet_links
        
        if debug:
            print(f"[DEBUG EZTV] Pattern 5 (direct magnet links) found {len(magnet_links)} magnet links in HTML")
            if magnet_links and len(magnet_links) > 0:
                print(f"[DEBUG EZTV] Sample magnet link (first 100 chars): {magnet_links[0][:100]}")
        
        # Also search for episode/show links that might lead to magnet links
        # Look for links that might be episode pages
        episode_links = re.findall(r'href=["\']([^"\']*ep/[^"\']+)["\']', data, re.IGNORECASE)
        if not episode_links:
            episode_links = re.findall(r'href=["\']([^"\']*episode[^"\']+)["\']', data, re.IGNORECASE)
        if not episode_links:
            # Look for any links that might be show pages
            episode_links = re.findall(r'href=["\']([^"\']*shows/[^"\']+)["\']', data, re.IGNORECASE)
        
        # Also look for any internal links that might be show pages (not search, static, css, js)
        # But be more specific - look for /shows/ or numeric IDs that might be show pages
        if not episode_links:
            all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', data, re.IGNORECASE)
            # Filter for internal links that look like show pages
            # Must contain /shows/ or be a numeric ID path like /123/ or /12345/
            episode_links = [link for link in all_hrefs 
                           if link.startswith('/') and 
                           not link.startswith('/search') and 
                           not link.startswith('/static') and
                           not link.startswith('/css') and
                           not link.startswith('/js') and
                           not link.startswith('/images') and
                           not link.startswith('/styles') and
                           not link.startswith('/countdown') and
                           not link.startswith('/calendar') and
                           not link.startswith('/forum') and
                           not link.startswith('/faq') and
                           not link.startswith('/login') and
                           not link.startswith('/api') and
                           not link.startswith('/cdn-cgi') and
                           not link.startswith('#') and
                           len(link) > 3 and
                           ('/shows/' in link.lower() or 
                            re.match(r'^/\d+/', link) or  # Starts with /123/
                            re.match(r'^/[^/]+/\d+', link))]  # Has numeric ID like /show/123
        
        if debug:
            print(f"[DEBUG EZTV] Found {len(episode_links)} potential episode/show links in entire HTML")
            if episode_links and len(episode_links) > 0:
                print(f"[DEBUG EZTV] Sample episode/show links: {episode_links[:3]}")
        
        # Look for download links or .torrent files
        download_links = re.findall(r'href=["\']([^"\']*\.torrent)["\']', data, re.IGNORECASE)
        if debug:
            print(f"[DEBUG EZTV] Found {len(download_links)} .torrent file links")
        
        # Look for magnet links in select option values (EZTV uses dropdowns)
        select_options = re.findall(r'<option[^>]*value=["\']([^"\']+)["\']', data, re.IGNORECASE)
        for opt_val in select_options:
            if 'magnet:' in opt_val.lower():
                magnet_links.append(opt_val)
                if debug:
                    print(f"[DEBUG EZTV] Found magnet link in select option")
        
        # Look for magnet links in JavaScript variables
        js_magnets = re.findall(r'["\'](magnet:\?[^"\']+)["\']', data, re.IGNORECASE)
        if js_magnets:
            magnet_links.extend(js_magnets)
            if debug:
                print(f"[DEBUG EZTV] Found {len(js_magnets)} magnet links in JavaScript")
        
        # Look for magnet links in data attributes
        data_attr_magnets = re.findall(r'data-[^=]*=["\'](magnet:\?[^"\']+)["\']', data, re.IGNORECASE)
        if data_attr_magnets:
            magnet_links.extend(data_attr_magnets)
            if debug:
                print(f"[DEBUG EZTV] Found {len(data_attr_magnets)} magnet links in data attributes")
        
        # Look for magnet links in onclick or other event handlers
        onclick_magnets = re.findall(r'onclick=["\'][^"\']*(magnet:\?[^"\']+)', data, re.IGNORECASE)
        if onclick_magnets:
            magnet_links.extend(onclick_magnets)
            if debug:
                print(f"[DEBUG EZTV] Found {len(onclick_magnets)} magnet links in onclick handlers")
        
        # Remove duplicates again after adding new sources
        seen = set()
        unique_magnet_links = []
        for link in magnet_links:
            if link not in seen:
                seen.add(link)
                unique_magnet_links.append(link)
        magnet_links = unique_magnet_links
        
        if debug:
            print(f"[DEBUG EZTV] Total unique magnet links found: {len(magnet_links)}")
        
        # Clean up data for table row parsing
        data_cleaned = data.replace('\t', '').replace('\n', '')
        
        # Try multiple patterns for finding torrent rows (use cleaned data)
        # Pattern 1: Original pattern
        items = re.findall(
            r'<tr[^>]*name=["\']hover["\'][^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
            data_cleaned,
            re.IGNORECASE | re.DOTALL
        )
        
        if debug:
            print(f"[DEBUG EZTV] Pattern 1 found {len(items)} items")
        
        # Pattern 2: Alternative row patterns
        if not items:
            items = re.findall(
                r'<tr[^>]*class=["\']forum_header_border["\'][^>]*>(.*?)</tr>',
                data_cleaned,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 2 found {len(items)} items")
        
        # Pattern 3: Generic table rows with magnet links
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?magnet:.*?)</tr>',
                data_cleaned,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 3 found {len(items)} items")
        
        # Pattern 4: Look for table rows with episode/show links
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?ep/.*?)</tr>',
                data_cleaned,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 4a (rows with ep/) found {len(items)} items")
        
        # Pattern 4b: Look for any table rows
        if not items:
            items = re.findall(
                r'<tr[^>]*>(.*?)</tr>',
                data_cleaned,
                re.IGNORECASE | re.DOTALL
            )
            if debug:
                print(f"[DEBUG EZTV] Pattern 4b (any table row) found {len(items)} items")
                # Filter out non-torrent rows (like search forms)
                filtered_items = []
                for item in items:
                    # Skip if it's clearly not a torrent row
                    if 'search' in item.lower() and 'form' in item.lower():
                        continue
                    if 'ep/' in item.lower() or 'episode' in item.lower() or 'download' in item.lower():
                        filtered_items.append(item)
                if filtered_items:
                    items = filtered_items
                    if debug:
                        print(f"[DEBUG EZTV] Filtered to {len(items)} potential torrent rows")
                    # Extract links from these filtered items that might be show pages
                    for item in filtered_items:
                        item_links = re.findall(r'href=["\']([^"\']+)["\']', item, re.IGNORECASE)
                        for link in item_links:
                            # Look for show page links in the table rows
                            if (link.startswith('/') and 
                                not link.startswith('/search') and
                                ('/shows/' in link.lower() or 
                                 re.match(r'^/\d+/', link) or
                                 re.match(r'^/[^/]+/\d+', link))):
                                if link not in episode_links:
                                    episode_links.append(link)
                                    if debug:
                                        print(f"[DEBUG EZTV] Found show page link in table row: {link}")
        
        # If we found episode links but no magnet links, try to fetch them
        # Also try if we have items but they don't contain magnet links
        if episode_links and not magnet_links:
            if debug:
                print(f"[DEBUG EZTV] No magnet links found, but found {len(episode_links)} episode links")
                print(f"[DEBUG EZTV] EZTV may require visiting individual episode pages to get magnet links")
                print(f"[DEBUG EZTV] This would require multiple HTTP requests per search")
            # For now, we'll try to use episode links as items and fetch them
            # But this is complex, so let's first see if we can find the structure
        
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
        
        # If we have episode links but no magnet links, try to fetch them
        # This will help even if we have items that don't contain magnet links
        if episode_links and not magnet_links:
            if debug:
                print(f"[DEBUG EZTV] No magnet links found, attempting to fetch episode/show pages - will need to fetch each page")
            # Limit to first 10 episode links to avoid too many requests
            for ep_link in episode_links[:10]:
                try:
                    # Make link absolute if needed
                    if ep_link.startswith('/'):
                        full_url = BASE_URL + ep_link
                    elif ep_link.startswith('http'):
                        full_url = ep_link
                    else:
                        full_url = BASE_URL + '/' + ep_link
                    
                    if debug:
                        print(f"[DEBUG EZTV] Fetching episode page: {full_url}")
                    
                    ep_data = self.module.http_get_request(full_url, timeout=10, debug=debug)
                    if ep_data:
                        # Look for magnet link in episode page
                        ep_magnets = re.findall(r'magnet:\?[^\'"\s<>"]+', ep_data, re.IGNORECASE)
                        if ep_magnets:
                            magnet_links.append(ep_magnets[0])
                            if debug:
                                print(f"[DEBUG EZTV] Found magnet link on episode page")
                except Exception as e:
                    if debug:
                        print(f"[DEBUG EZTV] Error fetching episode page: {e}")
                    continue
            
            if magnet_links:
                items = [f"magnet_link:{link}" for link in magnet_links[:50]]
                if debug:
                    print(f"[DEBUG EZTV] Created {len(items)} items from episode pages")
        
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
            
            # Extract magnet links from select options and JavaScript in this item
            if debug:
                print(f"[DEBUG EZTV] Processing item {items_with_magnet+1}, checking for select options and JavaScript...")
            
            # First, try to extract magnet links from JavaScript onchange handlers
            onchange_magnets = re.findall(r'onchange=["\']([^"\']*magnet:[^"\']+)["\']', item, re.IGNORECASE | re.DOTALL)
            if not onchange_magnets:
                # Try to find magnet links in any JavaScript in the item
                onchange_magnets = re.findall(r'(magnet:\?[^\'"\s<>"]+)', item, re.IGNORECASE)
            
            if onchange_magnets:
                if debug:
                    print(f"[DEBUG EZTV] Found {len(onchange_magnets)} magnet links in JavaScript/onchange")
                for magnet in onchange_magnets:
                    items_with_magnet += 1
                    if debug:
                        print(f"[DEBUG EZTV] Found magnet in JavaScript: {magnet[:80]}...")
                    try:
                        name = self.module.fix_name(self.module.magnet2name(magnet))
                        self.items.update({
                            name: {'seeds': '0', 'leeches': '?', 'link': magnet}
                        })
                        if debug:
                            print(f"[DEBUG EZTV] Added item from JavaScript: {name[:50]}...")
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG EZTV] Failed to parse magnet from JavaScript: {e}")
                continue  # Skip to next item if we found magnets in JS
            
            # Also check select options
            select_options_in_item = re.findall(r'<option[^>]*value=["\']([^"\']+)["\']', item, re.IGNORECASE)
            if debug:
                print(f"[DEBUG EZTV] Found {len(select_options_in_item)} select options in item")
                if select_options_in_item and len(select_options_in_item) > 0:
                    print(f"[DEBUG EZTV] First option value (first 150 chars): {select_options_in_item[0][:150]}")
            
            # Also get the full select element to see the onchange handler
            select_elements = re.findall(r'<select[^>]*>(.*?)</select>', item, re.IGNORECASE | re.DOTALL)
            if select_elements and debug:
                print(f"[DEBUG EZTV] Found {len(select_elements)} select elements")
                # Try to extract onchange handler
                onchange_handlers = re.findall(r'onchange=["\']([^"\']+)["\']', item, re.IGNORECASE)
                if onchange_handlers:
                    print(f"[DEBUG EZTV] onchange handler (first 200 chars): {onchange_handlers[0][:200]}")
                    # Try to extract magnet links from onchange handler
                    handler_magnets = re.findall(r'(magnet:\?[^\'"\s<>"]+)', onchange_handlers[0], re.IGNORECASE)
                    if handler_magnets:
                        if debug:
                            print(f"[DEBUG EZTV] Found {len(handler_magnets)} magnet links in onchange handler")
                        for magnet in handler_magnets:
                            items_with_magnet += 1
                            try:
                                name = self.module.fix_name(self.module.magnet2name(magnet))
                                self.items.update({
                                    name: {'seeds': '0', 'leeches': '?', 'link': magnet}
                                })
                                if debug:
                                    print(f"[DEBUG EZTV] Added item from onchange handler: {name[:50]}...")
                            except Exception as e:
                                if debug:
                                    print(f"[DEBUG EZTV] Failed to parse magnet from onchange: {e}")
                        continue  # Skip to next item
            
            for opt_val in select_options_in_item:
                if 'magnet:' in opt_val.lower():
                    # Found magnet link in select option
                    magnet = opt_val
                    items_with_magnet += 1
                    if debug:
                        print(f"[DEBUG EZTV] Found magnet in select option: {magnet[:80]}...")
                    try:
                        name = self.module.fix_name(self.module.magnet2name(magnet))
                        self.items.update({
                            name: {'seeds': '0', 'leeches': '?', 'link': magnet}
                        })
                        if debug:
                            print(f"[DEBUG EZTV] Added item from select option: {name[:50]}...")
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG EZTV] Failed to parse magnet from select: {e}")
                    continue  # Skip to next item
            
            # Look for any links in this item that might lead to episode/show pages
            # Try multiple patterns for episode/show links
            ep_links_in_item = re.findall(r'href=["\']([^"\']*(?:ep/|episode|shows/)[^"\']+)["\']', item, re.IGNORECASE)
            if not ep_links_in_item:
                # Look for any href links that might be episode/show pages
                all_links_in_item = re.findall(r'href=["\']([^"\']+)["\']', item, re.IGNORECASE)
                if debug:
                    print(f"[DEBUG EZTV] Found {len(all_links_in_item)} total links in item")
                    if all_links_in_item:
                        print(f"[DEBUG EZTV] Sample links: {all_links_in_item[:3]}")
                # Filter for links that look like episode/show pages
                ep_links_in_item = [link for link in all_links_in_item if any(x in link.lower() for x in ['ep/', 'episode', 'shows/', 'show/', 'tv/', '/shows/'])]
                # Also look for links that are not external and not common paths
                if not ep_links_in_item:
                    # Try to find any internal links that might be show pages
                    internal_links = [link for link in all_links_in_item 
                                     if link.startswith('/') and 
                                     not link.startswith('/search') and 
                                     not link.startswith('/static') and
                                     not link.startswith('/css') and
                                     not link.startswith('/js') and
                                     len(link) > 3]
                    if internal_links:
                        ep_links_in_item = internal_links[:3]  # Try first 3 internal links
                        if debug:
                            print(f"[DEBUG EZTV] Using {len(ep_links_in_item)} internal links as potential show pages")
            
            if debug:
                print(f"[DEBUG EZTV] Found {len(ep_links_in_item)} potential episode/show links in item")
                if ep_links_in_item:
                    print(f"[DEBUG EZTV] Sample episode/show link: {ep_links_in_item[0][:100]}")
            
            if ep_links_in_item:
                # Try to fetch episode page to get magnet link
                for ep_link in ep_links_in_item[:1]:  # Just try first one
                    try:
                        if ep_link.startswith('/'):
                            full_url = BASE_URL + ep_link
                        elif ep_link.startswith('http'):
                            full_url = ep_link
                        else:
                            full_url = BASE_URL + '/' + ep_link
                        
                        if debug:
                            print(f"[DEBUG EZTV] Fetching episode page from item: {full_url}")
                        
                        ep_data = self.module.http_get_request(full_url, timeout=10, debug=debug)
                        if ep_data:
                            # Look for magnet link in episode page
                            ep_magnets = re.findall(r'magnet:\?[^\'"\s<>"]+', ep_data, re.IGNORECASE)
                            if not ep_magnets:
                                # Try select options
                                ep_select_opts = re.findall(r'<option[^>]*value=["\']([^"\']+)["\']', ep_data, re.IGNORECASE)
                                for opt in ep_select_opts:
                                    if 'magnet:' in opt.lower():
                                        ep_magnets.append(opt)
                                        break
                            
                            if ep_magnets:
                                magnet = ep_magnets[0]
                                items_with_magnet += 1
                                try:
                                    name = self.module.fix_name(self.module.magnet2name(magnet))
                                    self.items.update({
                                        name: {'seeds': '0', 'leeches': '?', 'link': magnet}
                                    })
                                    if debug:
                                        print(f"[DEBUG EZTV] Added item from episode page: {name[:50]}...")
                                except Exception as e:
                                    if debug:
                                        print(f"[DEBUG EZTV] Failed to parse magnet from episode page: {e}")
                                break  # Found one, move to next item
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG EZTV] Error fetching episode page from item: {e}")
                continue  # Skip to next item
            
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
