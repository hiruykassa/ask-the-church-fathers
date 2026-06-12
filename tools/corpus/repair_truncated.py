"""Repair passages whose HCF source file was truncated upstream.

Many files in the HistoricalChristianFaith/Writings-Database repo are HTTrack
mirrors of CCEL that got cut off mid-text (e.g. Confessions Book IV stops at
"...my eight and twen"). The complete originals survive on the Wayback Machine,
in the exact same HTML format our parser already handles.

Strategy:
  1. Walk a local clone of the writings repo.
  2. For every CCEL-mirrored file whose *parsed body* ends mid-sentence, treat it
     as a truncation candidate and read the original CCEL URL from its mirror
     comment.
  3. Fetch the complete original from the Wayback Machine, re-parse it.
  4. Match the DB passage (work by source dir, passage by header) and update its
     text IN PLACE — only when the fresh body is meaningfully longer and ends on
     a sentence boundary (this filters out files that merely end on "Amen," etc.).

Usage (from project root, with a clone at /tmp/writings-db):
    git clone --depth 1 https://github.com/HistoricalChristianFaith/Writings-Database.git /tmp/writings-db
    python3 tools/corpus/repair_truncated.py --repo /tmp/writings-db [--dry-run] [--limit N]
"""

import argparse
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_github_writings import parse_html_file_content  # noqa: E402

DB_PATH = Path(__file__).resolve().parents[2] / "backend" / "database.db"
WRITINGS_TREE = "https://github.com/HistoricalChristianFaith/Writings-Database/tree/master/"
UA = "ask-the-early-church-repair/1.0 (corpus truncation repair)"


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


_TERMINAL = ".!?\"')"


def is_truncated_body(body: str) -> bool:
    """A repaired/complete body ends on sentence-terminating punctuation; a body
    cut mid-text does not. We strip the parser's trailing rule ("--------"),
    footnote-ref digits and "parparpar" artifacts before judging."""
    v = re.sub(r"(parparpar|par)+$", "", visible(body)).strip()
    v = v.rstrip("-–— \t0123456789")
    if len(v) < 50:
        return False
    return v[-1] not in _TERMINAL


def mirror_url(data: bytes) -> str | None:
    m = re.search(rb"Mirrored from (\S+) by HTTrack", data[:800])
    if not m:
        return None
    url = m.group(1).decode()
    return url if url.startswith("http") else "http://" + url


def fetch(url: str, timeout: int = 60, retries: int = 4) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            wait = 3 * (attempt + 1)  # archive.org throttles → back off
            if attempt < retries - 1:
                time.sleep(wait)
            else:
                print(f"      ! fetch failed after {retries}: {e}")
    return None


def wayback_original(ccel_url: str) -> bytes | None:
    """Fetch the raw (id_) Wayback capture closest to the 2004 HTTrack mirror."""
    api = "http://archive.org/wayback/available?" + urllib.parse.urlencode(
        {"url": ccel_url, "timestamp": "20041001"}
    )
    meta = fetch(api, timeout=30)
    ts = None
    if meta:
        m = re.search(rb'"timestamp"\s*:\s*"(\d+)"', meta)
        if m:
            ts = m.group(1).decode()
    for stamp in ([ts] if ts else []) + ["2005", "2006", "2004"]:
        snap = f"http://web.archive.org/web/{stamp}id_/{ccel_url}"
        data = fetch(snap)
        if data and len(data) > 1500:
            return data
    return None


def build_passage_index(conn):
    """Map (normalized source dir, normalized header) -> passage id."""
    cur = conn.cursor()
    rows = cur.execute(
        """SELECT p.id, p.header, p.text, w.source_url
           FROM passages p JOIN works w ON p.work_id = w.id"""
    ).fetchall()
    idx = {}
    for pid, header, text, surl in rows:
        if not surl or WRITINGS_TREE not in surl:
            continue
        rel = urllib.parse.unquote(surl.split(WRITINGS_TREE, 1)[1])
        idx[(rel, norm(header))] = (pid, len(visible(text or "")), is_truncated_body(text or ""))
    return idx


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/tmp/writings-db")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    repo = Path(args.repo)
    if not repo.is_dir():
        print(f"ERROR: repo not found: {repo}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    index = build_passage_index(conn)

    # Find truncated CCEL files.
    candidates = []
    for root, _, files in os.walk(repo):
        if "/.git" in root:
            continue
        for fn in files:
            if not fn.lower().endswith(".html"):
                continue
            p = Path(root) / fn
            data = p.read_bytes()
            if b"ccel.org" not in data[:800].lower():
                continue
            # The reliable cut signal: HTTrack-truncated mirrors stop mid-page and
            # never reach the closing </html>. Complete pages (even ones whose body
            # ends on a Greek footnote, a name list, or "etc.") always close it.
            if data.rstrip()[-7:].lower() == b"</html>":
                continue
            try:
                header, body = parse_html_file_content(data)
            except Exception:
                continue
            candidates.append((p, header, mirror_url(data)))

    print(f"Found {len(candidates)} truncated CCEL files.\n")
    if args.limit:
        candidates = candidates[: args.limit]

    repaired = skipped = unmatched = 0
    for p, header, url in candidates:
        rel_dir = urllib.parse.unquote(str(p.parent.relative_to(repo)))
        key = (rel_dir, norm(header))
        # Single-file works are stored with the file stem as the work dir suffix.
        if key not in index:
            alt = (f"{rel_dir}/{p.stem}", norm(header))
            key = alt if alt in index else key
        print(f"• {p.relative_to(repo)}  [{header!r}]")
        if key not in index:
            print("      - no matching DB passage (excluded author?) — skip")
            unmatched += 1
            continue
        pid, old_len, db_truncated = index[key]
        if not db_truncated:
            print(f"      - DB passage pid={pid} already complete — skip")
            skipped += 1
            continue
        if not url:
            print("      - no mirror URL — skip")
            skipped += 1
            continue
        data = wayback_original(url)
        if not data:
            print(f"      - no Wayback capture for {url} — skip")
            skipped += 1
            continue
        new_header, new_body = parse_html_file_content(data)
        new_len = len(visible(new_body))
        # A genuine repair recovers substantially more text. (The complete CCEL
        # bodies often end in Greek footnote text, so we can't require terminal
        # punctuation — the length jump is the reliable signal. Files that merely
        # ended on "Amen,"/"etc"/"&c.", and files where CCEL itself was truncated
        # at source, come back essentially the same length and are skipped.)
        if new_len < old_len + 500:
            print(f"      - fresh body not longer (old={old_len} new={new_len}) "
                  f"— CCEL source likely truncated too, skip")
            skipped += 1
            time.sleep(1)
            continue
        print(f"      ✓ pid={pid}  {old_len} -> {new_len} chars")
        if not args.dry_run:
            conn.execute("UPDATE passages SET text = ? WHERE id = ?", (new_body, pid))
            conn.commit()
        repaired += 1
        time.sleep(2)  # be gentle with the Wayback Machine

    print(f"\nrepaired={repaired} skipped={skipped} unmatched={unmatched} "
          f"({'DRY RUN' if args.dry_run else 'committed'})")
    conn.close()


if __name__ == "__main__":
    main()
