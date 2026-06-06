"""Smoke tests — run against a real database.db to catch deploy regressions.

These run in CI before every deploy. They don't exercise Voyage/Anthropic
(those are mocked implicitly by the empty-query path) — they just verify
that the app boots, the DB is wired in, and the security headers fire.

Run locally:
    cd backend && pytest -q
"""

import os
import sys

import pytest

# Make `import app` work whether pytest is launched from repo root or backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def client():
    from app import app  # imported lazily so missing keys don't crash collection
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["embeddings_loaded"] > 0


def test_authors(client):
    r = client.get("/api/authors")
    assert r.status_code == 200
    results = r.get_json()["results"]
    assert isinstance(results, list)
    assert len(results) >= 100  # corpus has ~126 authors


def test_search_empty_query(client):
    r = client.get("/api/search?q=")
    assert r.status_code == 200
    body = r.get_json()
    assert body["results"] == []
    assert body["author"] is None


def test_search_too_long(client):
    q = "a" * 501
    r = client.get(f"/api/search?q={q}")
    assert r.status_code == 400


def test_library_shape(client):
    r = client.get("/api/library")
    assert r.status_code == 200
    assert "sections" in r.get_json()


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in r.headers


def test_passage_404_for_unknown_id(client):
    r = client.get("/api/passages/999999999")
    assert r.status_code == 404
