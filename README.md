# Ask the Church Fathers

A full-stack web app for searching and reading the writings of the early Church Fathers.
Type a topic, keyword, or a Father's name — get matching passages, then ask an AI to synthesize what they collectively taught.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Features

- **Full-text search** — SQL `LIKE` matching across all passages in the database
- **Author detection** — queries like `"Augustine prayer"` auto-filter to that Father
- **Author filter chip** — click ✕ to broaden the search back to all authors
- **Grouped results** — passages grouped by author, each group collapsible
- **Save passages** — bookmark any passage to a personal Saved tab (session only)
- **AI synthesis** — streams a Claude-generated summary of what the Fathers collectively taught (3 short paragraphs, neutral scholarly tone, shows disagreements plainly)
- **Book reader** (`/read/:workId`) — full-screen reader with scroll-progress bar, sidebar/drawer TOC, and passage-level navigation; back button restores the last search
- **Scroll-reveal animations** — Father cards animate in as they enter the viewport
- **Full library catalog** — 36 Church Fathers plus Liturgies, Councils, Apocrypha, and Miscellaneous sections — all clickable to trigger a search

---

## Data Source

All passage data is scraped from **[New Advent — Church Fathers](https://www.newadvent.org/fathers/)** using `backend/etl.py` (`requests` + `BeautifulSoup4`). The ETL strips footnotes and annotations, splits text into paragraph-sized chunks, and inserts them into the SQLite database. `seed.py` provides a small set of sample passages for local development without running the full scrape.

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/
│   ├── app.py           # Flask API — 6 routes (see API section)
│   ├── database.py      # SQLite schema: authors, works, passages
│   ├── etl.py           # Scrapes newadvent.org → inserts into DB
│   ├── seed.py          # Sample data: Augustine, Chrysostom, Athanasius
│   ├── query.py         # Debug helper — prints passages to terminal
│   ├── database.db      # SQLite file (committed with seed data)
│   ├── requirements.txt # Python dependencies
│   └── .env             # Not committed — ANTHROPIC_API_KEY goes here
│
├── src/
│   ├── App.jsx                     # Root component — state, search, layout
│   ├── App.css                     # Full design system (CSS custom properties)
│   ├── ReadPage.jsx                # /read/:workId — book reader
│   ├── ReadPage.css                # Reader styles
│   ├── index.css                   # Global reset
│   ├── main.jsx                    # React Router: / and /read/:workId
│   │
│   ├── components/
│   │   ├── AccordionSection.jsx    # Collapsible catalog section
│   │   ├── AuthorCard.jsx          # Author result card with save/unsave
│   │   ├── FatherRow.jsx           # Single row in the Fathers accordion
│   │   ├── SavedView.jsx           # Saved passages tab
│   │   ├── SearchResults.jsx       # Results layout — count, chip, synthesis, cards
│   │   └── SynthesisPanel.jsx      # AI streaming synthesis panel
│   │
│   ├── constants/
│   │   ├── featuredFathers.js      # 10 featured fathers with portrait images
│   │   └── library.js              # ALL_FATHERS (36) + RIGHT_SECTIONS catalog
│   │
│   ├── data/
│   │   └── fathers.js              # 61-name list for author-detection logic
│   │
│   ├── hooks/
│   │   └── useScrollReveal.js      # IntersectionObserver → adds .is-visible on scroll
│   │
│   └── img/                        # Portrait JPEGs for 10 featured fathers
│
├── public/favicon.svg
├── index.html
├── vite.config.js
├── package.json
└── .gitignore
```

---

## Database Schema

```
authors   — id, name, born, died, tradition, bio
works     — id, author_id (FK), title, category, source_url
passages  — id, work_id (FK), text
```

---

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                   # Runs on http://localhost:5001
```

AI synthesis requires an Anthropic API key. Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Frontend

```bash
npm install
npm run dev                     # Runs on http://localhost:5173
```

---

## API Reference

| Method | Endpoint            | Description |
|--------|---------------------|-------------|
| GET    | `/api/health`       | Returns `{ "status": "ok" }` |
| GET    | `/api/search?q=`    | Full-text LIKE search — returns author, work, work_id, passage text |
| GET    | `/api/authors`      | All authors (id, name, tradition) |
| GET    | `/api/passages/:id` | Single passage by id |
| GET    | `/api/works/:id`    | All passages for a work (title, author, ordered passage list) |
| POST   | `/api/synthesize`   | Streams Claude synthesis. Body: `{ query, passages[] }` |

---

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7 |
| Styling  | Pure CSS custom properties — no Tailwind |
| Markdown | react-markdown |
| Icons    | react-icons (io5, md) |
| Backend  | Python 3, Flask, Flask-CORS, SQLite |
| AI       | Anthropic Claude (`claude-sonnet-4-6`), streamed via Flask `Response` generator |
| Scraping | requests + BeautifulSoup4 (source: newadvent.org) |
| Env vars | python-dotenv |

---

## How the AI Synthesis Works

1. Frontend sends the search topic and matching passages to `POST /api/synthesize`
2. Backend builds a prompt: act as a neutral patristic scholar — report exactly what the Fathers said, show disagreements plainly, no modern editorializing
3. Calls `client.messages.stream(model="claude-sonnet-4-6", ...)`
4. Flask streams each text chunk back via a Python generator
5. Frontend reads the stream with `response.body.getReader()` and appends chunks in real time via `react-markdown`

---

## How Author Detection Works

`detectAuthor(query)` in `App.jsx` scans the query against the 61-name list in `src/data/fathers.js`. Each word in a Father's name (minimum 5 characters) is tested against the query. On a match, the name is stripped from the search term — e.g. `"Augustine prayer"` sends `"prayer"` to the backend and filters results to Augustine client-side.
