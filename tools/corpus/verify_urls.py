#!/usr/bin/env python3
"""Verify suspected index pages that were misclassified as content."""

import urllib.request
import urllib.error
import ssl
import re
import time

BASE = "https://www.newadvent.org/fathers/"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            final_url = resp.geturl()
            if "fathers/" not in final_url:
                return None
            html = resp.read().decode("utf-8", errors="replace")
            return html
    except:
        return None

def get_title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else "Unknown"

VERIFY_IDS = ["2201", "2401", "2305", "2308", "2309", "2310", "1922"]

for work_id in VERIFY_IDS:
    print(f"\n=== Probing sub-pages for {work_id} ===")
    found = []
    consecutive_misses = 0
    for i in range(1, 100):
        sub_id = f"{work_id}{i:02d}"
        url = f"{BASE}{sub_id}.htm"
        html = fetch(url)
        if html is None:
            consecutive_misses += 1
            if consecutive_misses >= 3:
                break
            continue
        title = get_title(html)
        if "new advent" in title.lower() and "church fathers" not in title.lower():
            consecutive_misses += 1
            if consecutive_misses >= 3:
                break
            continue
        consecutive_misses = 0
        found.append(sub_id)
        if i % 10 == 0:
            print(f"  ...probed up to {sub_id}, found {len(found)} so far")
        time.sleep(0.2)
    
    if found:
        print(f"  INDEX confirmed: {len(found)} sub-pages")
        for s in found:
            print(f"  {BASE}{s}.htm")
    else:
        print(f"  CONTENT confirmed: no sub-pages found")
