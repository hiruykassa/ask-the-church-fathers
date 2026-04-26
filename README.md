# Ask the Church Fathers

A full-stack web app for searching and reading the writings of the early Church Fathers.
Type a topic, keyword, or a Father's name — get matching passages from 36 authors, then ask an AI to synthesize what they collectively taught.

---

## Features

- **Full-text search** — searches all passages in the database with SQL `LIKE` matching
- **Author detection** — queries like "Augustine prayer" automatically filter results to that Father and search by topic within his works
- **Author filter chip** — shown in results when a Father is detected; click ✕ to broaden the search
- **Grouped results** — passages are grouped by author, each group collapsible
- **Save passages** — bookmark any passage to a personal Saved tab (session memory, not persisted)
- **AI synthesis** — streams a Claude-generated summary of what the Fathers collectively taught on the topic (3 short paragraphs, neutral scholarly tone)
- **Book reader** (`/read/:workId`) — opens any work full-screen with:
  - Reading progress bar across the top
  - Sidebar table of contents (desktop) / drawer TOC (mobile)
  - Click any passage number to scroll directly to it
  - Back button returns to search results with the last query restored
- **Daily rotating quote** — hero quote changes each day, cycling through 7 quotes from the Fathers
- **Scroll-reveal animations** — Father cards animate in as they enter the viewport
- **Full library catalog** — 36 Church Fathers with all their works listed, plus Liturgies, Councils, Apocrypha, and Miscellaneous sections — all clickable to trigger a search

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/                        # Flask API + SQLite
│   ├── app.py                      # All API routes (see API section below)
│   ├── database.py                 # Creates the SQLite schema (authors, works, passages)
│   ├── seed.py                     # Seeds sample data: Augustine, Chrysostom, Athanasius
│   ├── etl.py                      # Scrapes newadvent.org and loads passages into the DB
│   ├── query.py                    # Debug helper — prints all passages to the terminal
│   ├── database.db                 # SQLite database file (committed with seed data)
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Not committed — put your ANTHROPIC_API_KEY here
│
├── src/                            # React 18 frontend (Vite)
│   │
│   ├── App.jsx                     # Root component — all state, search logic, layout
│   ├── App.css                     # Entire design system (CSS custom properties)
│   ├── ReadPage.jsx                # /read/:workId — full book reader
│   ├── ReadPage.css                # Reader-specific styles
│   ├── index.css                   # Global reset (overflow-x: clip)
│   ├── main.jsx                    # React Router setup — two routes: / and /read/:workId
│   │
│   ├── components/
│   │   ├── AccordionSection.jsx    # Reusable collapsible section (library catalog)
│   │   ├── AuthorCard.jsx          # One author's result card — expandable list of passages
│   │   ├── FatherRow.jsx           # Single row in the Fathers accordion (name + works)
│   │   ├── SavedView.jsx           # Saved passages tab — passages grouped by author
│   │   ├── SearchResults.jsx       # Results layout — count, author chip, synthesis, cards
│   │   └── SynthesisPanel.jsx      # AI synthesis panel with streaming display
│   │
│   ├── constants/
│   │   ├── quotes.js               # 7 rotating hero quotes (one shown per day)
│   │   ├── featuredFathers.js      # 10 featured fathers with portrait images
│   │   └── library.js             # ALL_FATHERS (36 entries) + RIGHT_SECTIONS catalog
│   │
│   ├── data/
│   │   └── fathers.js              # 61-entry name list used by the author-detection logic
│   │
│   ├── hooks/
│   │   └── useScrollReveal.js      # IntersectionObserver hook — adds .is-visible on scroll
│   │
│   └── img/                        # Portrait images for the 10 featured fathers
│       ├── augustine.jpeg
│       ├── athanasius.jpeg
│       ├── ignatius.jpeg
│       ├── irenaeus.jpeg
│       ├── chrysostom.jpeg
│       ├── justin-martyr.jpeg
│       ├── tertullian.jpeg
│       ├── basil.jpeg
│       ├── cyril.jpeg
│       └── origen.jpeg
│
├── public/
│   └── favicon.svg
├── index.html
├── vite.config.js
├── package.json
└── .gitignore
```

---

## Database Schema

Three tables managed by `database.py`:

```
authors   — id, name, born, died, tradition, bio
works     — id, author_id (FK), title, category, source_url
passages  — id, work_id (FK), text
```

The `etl.py` script scrapes [newadvent.org](https://www.newadvent.org/fathers/) using `requests` + `BeautifulSoup`, splits text into paragraph chunks, and inserts them into this schema. `seed.py` inserts a small set of hand-written sample passages for local development.

---

## Getting Started

### 1 — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The API runs at **http://localhost:5001**.

**AI synthesis** requires an Anthropic API key. Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2 — Frontend

```bash
# From the project root
npm install
npm run dev
```

The app runs at **http://localhost:5173**.

---

## API Reference

| Method | Endpoint               | Description |
|--------|------------------------|-------------|
| GET    | `/api/health`          | Health check — returns `{ "status": "ok" }` |
| GET    | `/api/search?q=`       | Full-text LIKE search across all passages. Returns author, work, work_id, and passage text. |
| GET    | `/api/authors`         | All authors in the database (id, name, tradition) |
| GET    | `/api/passages/:id`    | Single passage by id — includes author and work title |
| GET    | `/api/works/:id`       | All passages for a work — returns title, author, and ordered passage list |
| POST   | `/api/synthesize`      | Streams a Claude AI synthesis. Body: `{ query, passages[] }`. Response: plain text stream |

---

## Tech Stack

| Layer      | Technology |
|------------|-----------|
| Frontend   | React 18, Vite, react-router-dom v7 |
| Styling    | Pure CSS with custom properties — no Tailwind |
| Markdown   | react-markdown (used to render AI synthesis) |
| Icons      | react-icons (io5, md) |
| Backend    | Python 3, Flask, Flask-CORS, SQLite |
| AI         | Anthropic Claude (`claude-sonnet-4-6`), streamed via Flask `Response` generator |
| Scraping   | requests + BeautifulSoup4 |
| Env vars   | python-dotenv |

---

## How the AI Synthesis Works

The `/api/synthesize` endpoint:
1. Receives the search topic and the list of matching passages from the frontend
2. Builds a prompt instructing Claude to act as a neutral patristic scholar — report exactly what the Fathers said, show disagreements plainly, no modern editorializing
3. Calls `client.messages.stream(model="claude-sonnet-4-6", ...)` 
4. Returns a Flask `Response` with a Python generator that `yield`s each text chunk as it arrives
5. The frontend reads the stream with `response.body.getReader()` and appends each chunk to the displayed text in real time

---

## How Author Detection Works

`detectAuthor(query)` in `App.jsx` scans the raw query string against the 61-name list in `src/data/fathers.js`. It checks each word of each Father's name (minimum 5 characters to avoid false positives) against the query. When a match is found, the matched name is stripped from the search term so the backend receives the bare topic — e.g. `"Augustine prayer"` becomes a search for `"prayer"` filtered client-side to Augustine's results.

