"""Path to the runtime SQLite database (backend/database.db)."""
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "backend" / "database.db"
