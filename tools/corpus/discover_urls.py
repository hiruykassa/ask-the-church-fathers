#!/usr/bin/env python3
"""Discover all leaf content URLs for John Chrysostom's works on newadvent.org."""

import urllib.request
import urllib.error
import re
import time
import ssl

BASE = "https://www.newadvent.org/fathers/"
WORK_IDS = [
    "1901", "1902", "1903", "1904", "1905", "1906", "1907", "1908",
    "1909", "1910", "1911", "1912", "1913", "1914", "1915", "1916",
    "1917", "1918", "1919", "1920", "1921", "1922",
    "2001", "2101", "2102", "2201", "2202",
    "2301", "2302", "2303", "2304", "2305", "2306", "2307", "2308", "2309", "2310",
    "2401", "2402",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            final_url = resp.geturl()
            if "fathers/" not in final_url:
                return None, None
            html = resp.read().decode("utf-8", errors="replace")
            return html, resp.status
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
        return None, None

def get_title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = m.group(1).strip()
        title = re.sub(r"\s+", " ", title)
        return title
    return "Unknown"

def is_index_page(html):
    """Heuristic: index pages have links to sub-pages like XXXXNN.htm"""
    links = re.findall(r'href="(\d{6}\.htm)"', html)
    if links:
        return True
    links = re.findall(r'href="(\d{4}[a-z]\.htm)"', html)
    if links:
        return True
    body_text = re.sub(r'<[^>]+>', '', html)
    body_text = body_text.strip()
    if len(body_text) < 3000:
        return True
    return False

def find_subpage_links(html, work_id):
    """Extract sub-page links from an index page."""
    pattern = rf'href="({work_id}\d{{2}}\.htm)"'
    links = re.findall(pattern, html, re.IGNORECASE)
    pattern2 = rf'href="({work_id}[a-z]\.htm)"'
    links2 = re.findall(pattern2, html, re.IGNORECASE)
    return sorted(set(links + links2))

def probe_subpages(work_id):
    """Probe for sub-pages by testing sequential numbers and letter suffixes."""
    found = []
    for i in range(1, 150):
        sub_id = f"{work_id}{i:02d}"
        url = f"{BASE}{sub_id}.htm"
        html, status = fetch(url)
        if html is None:
            if i > 5:
                break
            continue
        title = get_title(html)
        if "new advent" in title.lower() and "church fathers" not in title.lower():
            if i > 5:
                break
            continue
        found.append(sub_id)
        if i % 10 == 0:
            print(f"  ...probed up to {sub_id}")
    
    for letter in "abcdefghijklmnopqrstuvwxyz":
        sub_id = f"{work_id}{letter}"
        url = f"{BASE}{sub_id}.htm"
        html, status = fetch(url)
        if html is None:
            continue
        title = get_title(html)
        if "new advent" in title.lower() and "church fathers" not in title.lower():
            continue
        found.append(sub_id)
    
    return found

def main():
    total_leaves = 0
    results = []
    
    for work_id in WORK_IDS:
        url = f"{BASE}{work_id}.htm"
        print(f"\nChecking {work_id}...", flush=True)
        html, status = fetch(url)
        
        if html is None:
            print(f"  INVALID (not found or redirected)")
            results.append({
                "work_id": work_id,
                "title": "INVALID",
                "type": "invalid",
                "leaves": [],
                "count": 0,
            })
            continue
        
        title = get_title(html)
        print(f"  Title: {title}")
        
        if "new advent" in title.lower() and "church fathers" not in title.lower():
            print(f"  INVALID (redirected to homepage)")
            results.append({
                "work_id": work_id,
                "title": "INVALID - redirected",
                "type": "invalid",
                "leaves": [],
                "count": 0,
            })
            continue
        
        linked_subs = find_subpage_links(html, work_id)
        is_idx = is_index_page(html)
        
        if linked_subs:
            print(f"  INDEX page - found {len(linked_subs)} linked sub-pages")
            print(f"  Probing for additional sub-pages...")
            probed = probe_subpages(work_id)
            all_subs = sorted(set([s.replace('.htm','') for s in linked_subs] + probed))
            print(f"  Total sub-pages found: {len(all_subs)}")
            results.append({
                "work_id": work_id,
                "title": title,
                "type": "index",
                "leaves": [f"{BASE}{s}.htm" for s in all_subs],
                "count": len(all_subs),
            })
            total_leaves += len(all_subs)
        elif is_idx:
            print(f"  Possibly INDEX (short content) - probing sub-pages...")
            probed = probe_subpages(work_id)
            if probed:
                print(f"  Found {len(probed)} sub-pages")
                results.append({
                    "work_id": work_id,
                    "title": title,
                    "type": "index",
                    "leaves": [f"{BASE}{s}.htm" for s in probed],
                    "count": len(probed),
                })
                total_leaves += len(probed)
            else:
                print(f"  CONTENT page (short but no sub-pages)")
                results.append({
                    "work_id": work_id,
                    "title": title,
                    "type": "content",
                    "leaves": [url],
                    "count": 1,
                })
                total_leaves += 1
        else:
            print(f"  CONTENT page")
            results.append({
                "work_id": work_id,
                "title": title,
                "type": "content",
                "leaves": [url],
                "count": 1,
            })
            total_leaves += 1
        
        time.sleep(0.3)
    
    print("\n" + "="*80)
    print("FINAL REPORT")
    print("="*80)
    
    for r in results:
        print(f"\nWORK_ID: {r['work_id']}")
        print(f"TITLE: {r['title']}")
        print(f"TYPE: {r['type']}")
        print(f"LEAF_URLS:")
        for leaf in r['leaves']:
            print(f"  {leaf}")
        print(f"COUNT: {r['count']}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL_LEAF_URLS: {total_leaves}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
