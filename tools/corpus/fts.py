"""Rebuild the passages FTS index using plain text (HTML stripped for search)."""

from scrape_utils import strip_html


def rebuild_fts(cursor):
    cursor.execute("DROP TABLE IF EXISTS passages_fts")
    cursor.execute(
        """
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            text, author_name, work_title,
            content='', content_rowid=id
        )
        """
    )
    cursor.execute(
        """
        SELECT p.id, p.text, a.name, w.title
        FROM passages p
        JOIN works w ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        """
    )
    rows = cursor.fetchall()
    for rowid, text, author_name, work_title in rows:
        cursor.execute(
            """
            INSERT INTO passages_fts(rowid, text, author_name, work_title)
            VALUES (?, ?, ?, ?)
            """,
            (rowid, strip_html(text), author_name, work_title),
        )
    print(f"Rebuilt passages_fts index ({len(rows)} rows)")
