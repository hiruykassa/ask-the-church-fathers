# Ask the Church Fathers

A full-stack web app for searching and exploring the writings of the early Church Fathers.
Search by topic, keyword, or Father's name — then ask an AI to synthesize what they collectively taught.

---

## Features

- **Full-text search** across 36 Church Fathers, liturgies, councils, apocrypha, and creeds
- **Author detection** — queries like "Augustine prayer" automatically filter results to that Father
- **AI synthesis** — streams a thematic summary of what the Fathers said on your topic (requires OpenAI key)
- **Book reader** — read any full work passage-by-passage with a table of contents
- **Save passages** — bookmark quotes to a personal Saved tab (session-only)
- **Daily quote** — rotating hero quote from the Fathers on each new day

---

## Project Structure

```
ask-the-church-fathers/
├── backend/                  # Flask API + SQLite database
│   ├── app.py                # API routes: /api/search, /api/works, /api/synthesize
│   ├── database.py           # SQLite connection helpers
│   ├── etl.py                # ETL pipeline for loading source texts
│   ├── query.py              # Full-text search logic
│   ├── seed.py               # Database seed script
│   └── requirements.txt      # Python dependencies
│
├── src/                      # React frontend (Vite)
│   ├── components/           # UI components
│   │   ├── AccordionSection.jsx  # Collapsible catalog section
│   │   ├── AuthorCard.jsx        # Search result card for one author
│   │   ├── FatherRow.jsx         # Single row in the Fathers accordion
│   │   ├── SavedView.jsx         # Saved passages view
│   │   ├── SearchResults.jsx     # Search results layout
│   │   └── SynthesisPanel.jsx    # AI synthesis panel
│   ├── constants/            # Static data
│   │   ├── featuredFathers.js    # 10 featured fathers with images
│   │   ├── library.js            # Full father list + catalog sections
│   │   └── quotes.js             # Rotating daily hero quotes
│   ├── data/
│   │   └── fathers.js            # Name list used by author detection
│   ├── hooks/
│   │   └── useScrollReveal.js    # IntersectionObserver scroll-reveal hook
│   ├── img/                  # Father portrait images
│   ├── pages/
│   ├── App.jsx               # Root component — state, routing, layout
│   ├── App.css               # Full design system (CSS custom properties)
│   ├── ReadPage.jsx          # /read/:workId — full book reader
│   ├── ReadPage.css          # Reader-specific styles
│   ├── index.css             # Global reset
│   └── main.jsx              # React Router setup
│
├── public/
│   └── favicon.svg
├── index.html
├── vite.config.js
└── package.json
```

---

## Getting Started

### 1 — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API will be available at **http://localhost:5001**.

> **Synthesis** requires an `OPENAI_API_KEY` environment variable:
> ```bash
> export OPENAI_API_KEY=sk-...
> python app.py
> ```

### 2 — Frontend

```bash
# from the project root
npm install
npm run dev
```

The app will be available at **http://localhost:5173**.

---

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Frontend  | React 18, Vite, react-router-dom v7 |
| Styling   | Pure CSS with custom properties     |
| Markdown  | react-markdown                      |
| Icons     | react-icons                         |
| Backend   | Python, Flask, SQLite               |
| AI        | OpenAI API (streaming)              |

---

## API Endpoints

| Method | Path                  | Description                          |
|--------|-----------------------|--------------------------------------|
| GET    | `/api/search?q=`      | Full-text search across all passages |
| GET    | `/api/works/:id`      | Fetch all passages for a work        |
| POST   | `/api/synthesize`     | Stream AI synthesis for passages     |

