# Ask the Early Church — Claude Code Plan

Three workstreams. Run them in order or in parallel. Each section is a self-contained Claude Code prompt you can paste or adapt.

---

## 1. Frontend: Kill the AI-Generated Feel

### Diagnosis

The current UI has the classic "AI built this" symptoms:
- **Over-tokenized color system** — 50+ CSS variables with names like `crossGoldSoft`, `parchment3`, `surface2`. Real designers use 8–12 color tokens.
- **Too many font families** — Cinzel + Cormorant Garamond + Crimson Text + Inter = 4 families with multiple weights. Pick 2 max.
- **Decorative overkill** — gold gradients, drop-shadow crosses, `radial-gradient(ellipse 80% 50%...)` hero glows, `color-mix()` everywhere. These scream "generated."
- **Every element is styled** — no visual breathing room. Every card has borders, shadows, gold accents, hover animations. A human designer would leave most things plain.
- **Symmetry everywhere** — centered hero, centered search, centered cards, centered footer. Real layouts have asymmetry and editorial rhythm.
- **Animation on everything** — `pageFadeIn`, `view-fade`, scroll reveal, fav-pop. Subtle is fine; animating every mount is not.

### Claude Code Prompt — Phase 1: Color & Typography Reset

```
Read src/theme/tokens.js, src/index.css, and src/App.css.

Simplify the design system:

TYPOGRAPHY:
- Remove Cormorant Garamond entirely. Use only TWO font families:
  - "Crimson Pro" (not Crimson Text — Pro has better weight range) for headings AND body prose
  - "Inter" for UI chrome (nav, buttons, labels, meta text)
- Import from Google Fonts: Crimson Pro 400,400i,500,600,700 and Inter 400,500,600
- Remove Cinzel entirely. The site title and headings should use Crimson Pro 600-700 instead. Cinzel is the #1 tell of AI-generated "old" sites.
- Body text: Crimson Pro 400, 19px, line-height 1.75
- All letter-spacing: reduce by 50% globally. The current 1.5-2px letter-spacing on uppercase labels is too much. Use 0.5-1px max.

COLORS — collapse to this palette:
Light mode:
  --bg: #faf8f5 (warm white, less yellow than current)
  --surface: #ffffff
  --text: #1a1a1a
  --text-secondary: #666660
  --text-tertiary: #999990
  --accent: #8b6914 (muted gold, NOT bright orange-gold)
  --accent-soft: rgba(139, 105, 20, 0.08)
  --border: #e8e6e1
  --border-light: #f0eeea
  --header-bg: #2c2416 (dark brown)
  --header-text: #f0ebe3

Dark mode:
  --bg: #111110
  --surface: #1a1918
  --text: #e8e6e1
  --text-secondary: #999990
  --text-tertiary: #666660
  --accent: #d4a840 (slightly brighter gold for contrast)
  --accent-soft: rgba(212, 168, 64, 0.10)
  --border: #2a2928
  --border-light: #222120
  --header-bg: #1a1716
  --header-text: #e8e6e1

Remove ALL other color tokens (crossGold, crossGoldSoft, crossGlow, parchment, parchment2, parchment3, heroGlow, heroGlowGold, favoriteHi, favoriteSoft, goldHi, goldSoft, etc.). The favorites color should just be a simple --favorite: #dc3545.

Update applyWebTheme.js to use the reduced set. Delete unused CSS variable references in App.css.
```

### Claude Code Prompt — Phase 2: Layout & Visual Cleanup

```
Read src/App.css and src/ReadPage.css completely.

Make these changes to remove the AI-generated aesthetic:

HERO SECTION:
- Remove the radial-gradient hero glow entirely
- Remove the cross image from the hero (or make it much smaller, ~48px, and desaturated)
- Remove the blockquote from the hero. Just show the search bar with a single line above it: "Search 107,000+ passages from the early Church Fathers" in Inter 400 14px, --text-secondary
- The search bar should be the visual focus. Make it larger: 56px tall, 18px font, very subtle border (1px solid var(--border)), no box-shadow until focus
- Remove the "SEARCH" button inside the bar — just use Enter to search (add a subtle search icon on the left). This is cleaner.

CARDS & RESULTS:
- Remove the rank number column from result cards. Just show results in order.
- Remove ALL box-shadow from cards in their default state. Only add a very subtle shadow on hover: 0 1px 3px rgba(0,0,0,0.08)
- Remove the gold left-border accent from quote blocks. Use a simple 2px #ddd left border.
- Result cards: remove the border entirely. Use a subtle bottom border (1px solid var(--border-light)) between results instead. Think Google search results, not material design cards.

FEATURED FATHERS:
- Remove the portrait grid or redesign it. Current square cards with tiny names feel like a generated component. Instead: a horizontal scrollable row of just names (like tags/pills), no images. E.g.: "Augustine · Chrysostom · Athanasius · Origen · Jerome · ..."
- Or: keep portraits but make them circular, smaller (64px), in a single row with overflow-x scroll

HEADER:
- Remove the centered absolute-positioned title. Left-align the site name.
- "Ask the Early Church" in Crimson Pro 600, 18px, left side
- Nav tabs (Search, Saved) on the right side
- Remove the ornament subtitle "What did the early church teach"

ANIMATIONS:
- Remove pageFadeIn and view-fade animations
- Remove scroll-reveal (the IntersectionObserver-based fade-in)
- Keep only: hover transitions (opacity, color) at 150ms, and the accordion open/close

SPACING:
- Increase whitespace between sections. Current padding is tight and cluttered.
- Main content max-width: 680px for prose readability (not 880px or 1100px)
- Search results max-width: 720px

DARK MODE:
- Pure black (#111110) background — you already have this but the sections have subtle background bands (sectionBg, catalogBg). Remove those. One background color everywhere.
- Cards in dark mode: #1a1918 surface, 1px border rgba(255,255,255,0.08). No gold-tinted borders.
- Remove ALL html[data-theme='dark'] overrides for full-bleed section bands

FOOTER:
- Simple and small. One line: "Ask the Early Church · About · Contact" in Inter 13px, --text-tertiary
- Light gray top border, 32px padding. No dark brown background — just use --bg.
```

### Claude Code Prompt — Phase 3: Read Page Polish

```
Read src/ReadPage.css.

The reading experience is actually decent. Refine it:
- Keep Crimson Pro as the body font, 19px, line-height 1.85, max-width 680px
- Remove the scroll progress bar at the top (it's a common AI-generated pattern)
- Table of contents sidebar: keep it, but use simpler styling. Remove the card wrapper (toc-card). Just a plain list with 13px Inter text.
- Section headers within text: Crimson Pro 600, 1.1rem, no border-bottom, just margin-top 2.5em
- Remove text-align: justify and hyphens: auto from passages. Use text-align: left. Justified text with hyphens is a typography anti-pattern on the web.
- Passage highlight (from search): use a subtle yellow background (#fef9e7 light / #2a2518 dark) instead of gold with box-shadow
```

---

## 2. Database: Missing Authors & Text Quality

**Scope rule: strictly ≤ 451 AD (Council of Chalcedon).** Every author must have died by 451, OR been an active participant at Chalcedon itself (Theodoret d. 457 and Leo the Great d. 461 qualify — they were key voices at the council). No post-Chalcedon authors (no John Climacus, no Maximus the Confessor, no Pseudo-Dionysius).

### Current State
- 125 authors, 414 works, 107,347 passages, 108,118 embeddings
- Strong coverage of major Latin/Greek Fathers (Augustine 47 works, Chrysostom 36, Tertullian 33)
- **Weak spots:** Basil has only 1 work (De Spiritu Sancto), Epiphanius has only excerpts (11 passages), desert fathers are almost entirely absent, several major works from key Fathers are missing

### Claude Code Prompt — Phase A: Add Missing Desert Fathers & Monastics

```
Read tools/corpus/etl.py, tools/corpus/scrape_utils.py, and tools/corpus/ccel_urls.py fully.
Understand the scrape_work() pattern and fetch_and_parse() pipeline.

Create tools/corpus/add_desert_fathers.py that adds the following authors and works.
Use the same idempotent pattern: check if author/work exists before inserting.
Sources: New Advent (newadvent.org/fathers/), CCEL (ccel.org), and tertullian.org/fathers/ (Roger Pearse's "Additional Fathers" collection has public-domain English translations).

DESERT FATHERS & MONASTICS TO ADD:

1. Saint Moses the Black (Moses the Ethiopian) — d. 405, Eastern
   - His sayings from the Apophthegmata Patrum (Sayings of the Desert Fathers)
   - Source: The alphabetical collection — look for the "Moses" section
   - Also appears in Palladius's Lausiac History (ch. 19) — you already have Palladius but cross-reference

2. Saint Antony the Great — d. 356, Eastern
   - Life of Antony by Athanasius is already in your DB (check under Athanasius's works)
   - MISSING: The Letters of Antony (7 letters, important monastic texts)
   - MISSING: His sayings from the Apophthegmata Patrum ("Antony" section)

3. The Apophthegmata Patrum (Sayings of the Desert Fathers) — compiled ~5th century
   - This is THE core desert fathers text. Add as a single work attributed to "The Desert Fathers" (collective)
   - born: 350, died: 450, tradition: Eastern
   - Contains sayings of: Antony, Arsenius, Agathon, Moses, Poemen, Macarius, Sisoes, Syncletica (desert mother), Sarah (desert mother), Theodora (desert mother), and dozens more
   - Source: The alphabetical collection is available at tertullian.org/fathers/ (E. A. Wallis Budge translation) and also at various open-source sites
   - If a full translation isn't scrapable, use the selections in Cassian's Conferences as a starting point

4. Evagrius Ponticus — d. 399, Eastern
   - Praktikos (The Monk / Chapters on Practice) — foundational text on the eight logismoi (thoughts/passions)
   - Chapters on Prayer (also called "On Prayer", 153 chapters)
   - To Monks (Ad Monachos)
   - Sources: tertullian.org/fathers/ has some Evagrius; also check ccel.org/ccel/pearse/morefathers/

5. Saint Pachomius — d. 348, Eastern
   - The Rule of Pachomius (first cenobitic monastic rule)
   - Letters (fragments survive in English)
   - Source: tertullian.org/fathers/ or ccel.org additional fathers

6. Abba Dorotheos of Gaza — d. ~420, Eastern  
   - Instructions (Discourses) — if available in English translation pre-451
   - Note: some date him later (~560). ONLY include if you can confirm d. ≤ 451. If uncertain, SKIP.

7. Saint Syncletica of Alexandria — d. ~350, Eastern
   - Sayings (from the Apophthegmata Patrum — she's one of the desert mothers)
   - Life of Syncletica (attributed to Athanasius, probably pseudonymous)

8. Mark the Ascetic (Mark the Monk) — d. ~430, Eastern
   - "On the Spiritual Law" (200 chapters)
   - "On Those Who Think They Are Justified by Works"
   - Source: tertullian.org/fathers/ (Philokalia translations are later, but the original texts are pre-451)

9. Nilus of Sinai (Nilus the Elder / Nilus of Ancyra) — d. ~430, Eastern
   - Ascetic Discourse
   - Letters (selections)
   - Source: newadvent.org or tertullian.org

10. Diadochus of Photice — d. ~468 — BORDERLINE. He wrote "On Spiritual Knowledge" (100 chapters) around 450. Include ONLY if you treat him like Leo/Theodoret (active at Chalcedon era). Otherwise skip.

IMPORTANT NOTES:
- For the Apophthegmata Patrum: the sayings are organized alphabetically by father. Each father's section should be stored as a separate passage group (use the father's name as the header). This makes search useful — "Moses the Black on humility" should return his specific sayings.
- For all desert father texts: these are SHORT (often 1-3 sentences per saying). Don't merge them into giant passages. Keep individual sayings as individual passages where possible, or group by father with clear headers.
- Set section = 'Father' for all individual desert fathers, section = 'Miscellaneous' for the collective Apophthegmata if stored as its own work.
```

### Claude Code Prompt — Phase B: Fill Gaps in Major Fathers (≤ 451 AD only)

```
Read tools/corpus/etl.py and tools/corpus/ccel_urls.py.

These EXISTING authors are missing major works. Add them:

BASIL THE GREAT (d. 379) — currently only De Spiritu Sancto (224 passages):
  - Hexaemeron (Nine Homilies on the Six Days of Creation) — newadvent.org/fathers/3201.htm through 3209.htm
  - Letters — NPNF2-08 on CCEL (ccel.org/ccel/schaff/npnf208). Key letters: 38, 188, 189, 199, 210, 236
  - Against Eunomius (3 books) — significant trinitarian theology
  - Homilies on the Psalms — newadvent.org/fathers/
  - The Moralia — 80 rules of Christian life
  - The Long Rules and Short Rules (monastic) — newadvent.org/fathers/

EPIPHANIUS OF SALAMIS (d. 403) — currently only 11 passages (excerpts!):
  - The Panarion (Adversus Haereses) — massive heresiological work. Full text available at tertullian.org/fathers/ (Frank Williams translation sections). Even adding Books I-III substantially would be huge.
  - The Ancoratus — shorter doctrinal summary, also at tertullian.org

HILARY OF POITIERS (d. 367) — currently 2 works:
  - On the Councils (De Synodis) — newadvent.org/fathers/3303.htm
  - Homilies on the Psalms — if not already included

CYRIL OF JERUSALEM (d. 386) — 1 work, 722 passages:
  - Verify: are all 23 Catechetical Lectures + 5 Mystagogical Catecheses complete?
  - Run: SELECT header, COUNT(*) FROM passages WHERE work_id = (SELECT id FROM works WHERE title LIKE '%Catechetical%' OR title LIKE '%Cyril%' LIMIT 1) GROUP BY header ORDER BY header
  - If any lectures are missing, fill from newadvent.org/fathers/310101.htm through 310123.htm (catechetical) and 310601.htm through 310605.htm (mystagogical)

JOHN CASSIAN (d. 435) — 3 works:
  - Verify Conferences covers all 24 conferences (not just selections)
  - Verify Institutes covers all 12 books
  - Missing: "On the Incarnation Against Nestorius" (7 books) — newadvent.org/fathers/3508.htm

EPHRAIM THE SYRIAN (d. 373) — 7 works:
  - Verify Hymns on the Nativity, Hymns on Faith, Hymns on Paradise are complete
  - Missing: Hymns Against Heresies, Commentary on the Diatessaron (partial English available)

LEO THE GREAT (d. 461, Chalcedon participant):
  - Already has Sermons (435 passages) and Letters (449 passages) — GOOD
  - Verify: Is the Tome to Flavian (Letter 28) included? This is THE most important single letter for Chalcedonian Christology. Run: SELECT text FROM passages WHERE work_id IN (SELECT id FROM works WHERE author_id=(SELECT id FROM authors WHERE name='Leo the Great') AND title LIKE '%Letter%') AND (text LIKE '%Flavian%' OR text LIKE '%tome%') LIMIT 3

COUNCILS — verify completeness:
  - Council of Nicaea I (325): only 31 passages. Should have the Creed + 20 canons + synodal letter. If only canons, add the creed and letter.
  - Council of Constantinople I (381): only 11 passages. Should have the Niceno-Constantinopolitan Creed + canons + synodal letter.
  - Council of Ephesus (431): 156 passages. Verify it includes Cyril's Twelve Anathemas and the Acts, not just canons.
  - Council of Chalcedon (451): 234 passages. Verify it includes the Definition of Chalcedon (the Chalcedonian Definition of Faith). This is arguably the most important single document for your site's scope.

Create tools/corpus/add_missing_works.py:
1. Scrapes each missing work from the appropriate source
2. Uses fetch_and_parse() from scrape_utils.py
3. Checks if work already exists before inserting (idempotent)
4. Prints a summary of what was added
```

### Claude Code Prompt — Phase C: Remove Post-451 Content & Audit Dates

```
Read backend/database.py.

Run this audit to ensure strict ≤451 scope:

python3 -c "
import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Authors who died after 451 and were NOT Chalcedon participants
print('=== POST-CHALCEDON AUTHORS TO REVIEW ===')
for r in c.execute('''
    SELECT a.name, a.died, a.tradition, COUNT(w.id) as works
    FROM authors a 
    LEFT JOIN works w ON w.author_id = a.id
    WHERE a.died > 451
    GROUP BY a.id ORDER BY a.died
''').fetchall():
    print(f'  {r[0]} (d. {r[1]}, {r[2]}) — {r[3]} works')
conn.close()
"

Current post-451 authors:
- Theodoret (d. 457) — KEEP. Active Chalcedon participant, all his works are pre-451 or Chalcedon-era.
- Leo the Great (d. 461) — KEEP. Wrote the Tome to Flavian (449), presided over Chalcedon by legates.

If any other post-451 authors appear, evaluate case by case:
- If the author's major works were written before 451, keep them.
- If the author is primarily post-Chalcedon, remove them.

Also verify no works have wrong date assignments. Spot-check:
python3 -c "
import sqlite3
conn = sqlite3.connect('database.db')
c = conn.cursor()
# Works where author death year seems wrong
for r in c.execute('''
    SELECT a.name, a.born, a.died FROM authors a
    WHERE a.died IS NOT NULL AND a.born IS NOT NULL AND (a.died - a.born) > 120
''').fetchall():
    print(f'  SUSPICIOUS LIFESPAN: {r[0]} born {r[1]} died {r[2]} ({r[2]-r[1]} years)')
conn.close()
"
Note: Many "authors" like "Acts of Thomas" or "Gospel of Nicodemus" use born=died as a rough composition date. That's fine.
```

### Claude Code Prompt — Phase D: Text Quality Cleanup

```
Read backend/clean_editorial_notes.py and backend/utils.py.

The text quality issues to fix:

1. EDITORIAL BIAS AUDIT:
   Run a sample check on 30 random passages:
   python3 -c "
   import sqlite3
   conn = sqlite3.connect('database.db')
   c = conn.cursor()
   rows = c.execute('SELECT p.id, p.text, a.name, w.title FROM passages p JOIN works w ON p.work_id=w.id JOIN authors a ON w.author_id=a.id ORDER BY RANDOM() LIMIT 30').fetchall()
   for r in rows:
       print(f'--- {r[2]} / {r[3]} (id={r[0]}) ---')
       print(r[1][:500])
       print()
   conn.close()
   "

   Look for and flag:
   - Schaff/Wace editorial introductions mixed into passage text ("The following treatise...", "This work is attributed to...")
   - Translator footnotes not properly stripped (numbered footnotes, bracketed annotations like "[Ed. note:...]")
   - HTML artifacts (<br>, &amp;, &nbsp; etc.) in stored text
   - Modern editorial framing that isn't the Father's own words ("This shows that the early church believed...", "It is clear from this passage that...")
   - Passages that are just cross-references, page numbers, or empty stubs
   - Protestant editorial commentary in Schaff's notes (e.g. dismissive comments about saints, relics, monasticism, or Marian doctrine — the primary text should speak for itself)

2. HTML CLEANUP:
   Create backend/deep_clean.py that:
   - Finds all passages still containing HTML tags: SELECT id, text FROM passages WHERE text LIKE '%<%'
   - Strips them properly using BeautifulSoup (preserve paragraph breaks as \n\n)
   - Removes empty or near-empty passages (< 20 chars after stripping)
   - Removes passages that are ONLY editorial headers/footnotes with no actual Father's text
   - Logs every change with passage ID and before/after preview

3. COMPLETENESS CHECK:
   For each of the top 15 authors by work count, verify major works have reasonable passage counts.
   A "book" of Against Heresies should have 30-80 passages. Flag any major work with < 5 passages as a probable failed scrape.
   
   Also check for duplicate passages:
   SELECT text, COUNT(*) as ct FROM passages GROUP BY text HAVING ct > 1 ORDER BY ct DESC LIMIT 20
   Remove exact duplicates (keep the lowest ID).

4. After ALL changes (phases A-D), rebuild FTS and re-embed:
   cd tools/corpus && python3 fts.py
   cd backend && python3 embed_passages.py
   
   embed_passages.py should skip already-embedded passages and only embed new ones.
   Estimated Voyage cost for ~5,000 new passages: ~$0.50-1.00.
```

### Summary: What This Adds

| Category | Currently | After |
|----------|-----------|-------|
| Desert Fathers (Moses, Antony, Pachomius, etc.) | ~0 dedicated | 8-10 authors + Apophthegmata |
| Evagrius Ponticus | missing | Praktikos, On Prayer, Ad Monachos |
| Basil the Great | 1 work | 6-8 works |
| Epiphanius of Salamis | 11 passages | hundreds (Panarion + Ancoratus) |
| Desert Mothers (Syncletica, Sarah, Theodora) | 0 | included via Apophthegmata |
| Mark the Ascetic, Nilus of Sinai | 0 | 2-3 works each |
| Council documents verified complete | unclear | verified with Definition of Chalcedon |

---

## 3. Search: Cost Efficiency & Bot Protection

### Current Cost Structure
- **Every search** calls Haiku (~$0.001) for query parsing + Voyage (~$0.0001) for embedding = ~$0.0011/search
- At $25/mo, that's ~22,000 searches/month budget
- Rate limit: 10 searches/minute per IP (good)

### Claude Code Prompt — Reduce API Costs

```
Read backend/app.py and backend/search_cache.py completely.

Implement these cost reductions:

1. CLIENT-SIDE QUERY PARSING (eliminate Haiku calls for simple queries):
   Most queries are simple keyword searches that don't need AI parsing.
   
   In app.py, add a rule-based pre-parser before calling Haiku:
   
   def try_local_parse(raw_query, author_names):
       """Try to parse locally; return None if ambiguous (needs Haiku)."""
       q = raw_query.strip()
       
       # Direct author name match
       q_lower = q.lower()
       for name in author_names:
           if name.lower() == q_lower:
               return {"author": name, "keywords": ""}
           # "Augustine on grace" pattern
           if q_lower.startswith(name.lower() + " on "):
               topic = q[len(name) + 4:].strip()
               return {"author": name, "keywords": topic}
           if q_lower.startswith(name.lower() + " "):
               rest = q[len(name) + 1:].strip()
               return {"author": name, "keywords": rest}
       
       # Pure keyword search (no author mentioned) — skip Haiku entirely
       # Check if any author name appears in the query
       has_author = False
       for name in author_names:
           parts = name.lower().split()
           if any(p in q_lower.split() for p in parts if len(p) > 3):
               has_author = True
               break
       
       if not has_author:
           return {"author": "none", "keywords": q}
       
       # Ambiguous — fall through to Haiku
       return None
   
   Then in parse_user_query_safe, try local parse first:
   
   def parse_user_query_safe(raw_query, author_names):
       cache_key = _cache_key("parse", raw_query)
       cached = parse_cache.get(cache_key)
       if cached is not None:
           return cached
       
       # Try local parse first (free)
       local = try_local_parse(raw_query, author_names)
       if local is not None:
           parse_cache.set(cache_key, local)
           return local
       
       # Fall back to Haiku
       try:
           parsed = parse_user_query(raw_query, author_names)
       except Exception as exc:
           log.warning("Query parse failed: %s", exc)
           parsed = {"author": "none", "keywords": raw_query}
       
       parse_cache.set(cache_key, parsed)
       return parsed
   
   This should eliminate 60-80% of Haiku calls.

2. INCREASE CACHE TTL:
   In search_cache.py, change default TTL from 3600 (1hr) to 86400 (24hrs).
   The corpus doesn't change at runtime, so cached results stay valid indefinitely.
   Also increase cache sizes:
   - EMBED_CACHE_SIZE: 2048 (was 1024)
   - PARSE_CACHE_SIZE: 2048 (was 512)  
   - HYBRID_CACHE_SIZE: 2048 (was 512)
   - FTS_CACHE_SIZE: 2048 (was 512)

3. FTS-ONLY FALLBACK:
   If Voyage embedding fails or is slow, fall back to FTS-only search.
   This is already partially handled but make it explicit:
   
   In hybrid_search(), if vector_search returns empty (Voyage failure),
   return FTS results directly instead of empty.

4. BATCH EMBEDDING AT BUILD TIME:
   All passages should be pre-embedded (you already have embed_passages.py).
   Verify: SELECT COUNT(*) FROM passages WHERE id NOT IN (SELECT passage_id FROM embeddings)
   If any are missing, run embed_passages.py to fill gaps.
   At search time, only the QUERY needs embedding (1 Voyage call), not passages.
```

### Claude Code Prompt — Bot Protection

```
Read backend/app.py, specifically the rate limiting setup.

Add these protections:

1. STRICTER RATE LIMITS:
   Change search rate limit from "10 per minute" to "6 per minute" per IP.
   Add a daily cap: "200 per day" per IP.
   
   @app.route("/api/search")
   @limiter.limit("6 per minute;200 per day", override_defaults=True)
   def search():

2. QUERY VALIDATION (already have MAX_QUERY_LENGTH=500, good):
   Add: reject queries that are clearly bot probes:
   
   # After the length check in search():
   if re.search(r'[\x00-\x1f]', q):  # control characters
       return jsonify({"error": "Invalid query"}), 400
   if len(q.split()) > 50:  # no natural query has 50+ words
       return jsonify({"error": "Query too long"}), 400

3. ADD CORS ORIGIN VALIDATION:
   Your CORS is already configured with ALLOWED_ORIGIN. Good.
   Make sure in production this is set to your actual domain, not localhost.

4. ADD REQUEST COSTING HEADERS:
   Return headers that tell the frontend how much budget is left:
   
   @app.after_request
   def add_rate_headers(response):
       # Flask-Limiter already adds X-RateLimit headers
       return response

5. CONSIDER: For production, use Cloudflare in front of your API.
   Cloudflare's free tier gives you:
   - Bot detection (blocks known scrapers)
   - DDoS protection
   - Rate limiting at the edge (before requests hit your server)
   - This is the single most impactful thing for bot protection.

6. OPTIONAL — API KEY FOR FRONTEND:
   Add a simple static API key that the frontend sends:
   
   API_KEY = os.getenv("FRONTEND_API_KEY", "dev-key")
   
   @app.before_request
   def check_api_key():
       if request.path.startswith("/api/search") or request.path.startswith("/api/synthesize"):
           key = request.headers.get("X-API-Key", "")
           if key != API_KEY:
               return jsonify({"error": "Unauthorized"}), 401
   
   This isn't real security (the key is in your JS bundle), but it stops
   casual curl/script abuse. Combined with Cloudflare, it's sufficient.
   
   In the frontend (src/api/client.js), add the header:
   fetch(url, { headers: { "X-API-Key": "your-key-here" } })
```

---

## Execution Order

1. **Frontend Phase 1** (typography + colors) — 30 min, biggest visual impact
2. **Frontend Phase 2** (layout cleanup) — 1-2 hrs, requires careful CSS work
3. **Search cost reduction** — 30 min, immediate money savings
4. **Bot protection** — 20 min
5. **Database audit** — 1 hr to assess, then hours/days for scraping
6. **Database text cleanup** — 1-2 hrs
7. **Frontend Phase 3** (read page) — 30 min
8. **Re-embed** after database changes — depends on passage count, ~$2-5 in Voyage costs

## Key Principle

The #1 thing that makes a site look AI-generated is **too much design**. Real designers exercise restraint. When in doubt, remove decoration, reduce color variety, increase whitespace, and use fewer font weights.
