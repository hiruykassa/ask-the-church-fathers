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


# ── Response caching for immutable reference data ─────────────────────────────
# The corpus cannot change without a redeploy, so these responses are cacheable.
# The interesting assertions are the *negative* ones: search and health must
# never acquire a Cache-Control header, and non-200s must never be cached.

def test_reference_endpoints_are_cacheable(client):
    for path in ("/api/library", "/api/authors", "/api/categories",
                 "/api/scripture/books"):
        r = client.get(path)
        assert r.status_code == 200, path
        cc = r.headers.get("Cache-Control", "")
        assert "public" in cc, f"{path} missing public: {cc!r}"
        assert "max-age=" in cc, f"{path} missing max-age: {cc!r}"
        # A shared cache must not reuse one origin's CORS response for another.
        assert "Origin" in r.headers.get("Vary", ""), path


def test_search_is_never_cached(client):
    # Search can degrade to fewer results on a transient provider failure and
    # still return 200. Caching that would pin the degraded answer.
    r = client.get("/api/search?q=")
    assert r.status_code == 200
    assert "Cache-Control" not in r.headers


def test_health_is_never_cached(client):
    # A cached health check is not a health check.
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "Cache-Control" not in r.headers


def test_error_responses_are_not_cached(client):
    # Caching a 404 (or a 429) would pin the failure for the full max-age.
    r = client.get("/api/passages/999999999")
    assert r.status_code == 404
    assert "Cache-Control" not in r.headers


def test_csp_matches_the_cloudfront_policy(client):
    # The API and the CloudFront Response Headers Policy
    # (infra/response-headers-policy.json) must not drift — a directive present
    # on one surface and missing on the other is how a gap gets overlooked.
    csp = client.get("/api/health").headers["Content-Security-Policy"]
    for directive in (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "form-action 'self'",
        "script-src 'self'",
        "frame-ancestors 'none'",
    ):
        assert directive in csp, f"CSP missing {directive!r}: {csp!r}"


def test_hsts_is_not_sent_outside_production(client):
    # Sending HSTS from the plain-HTTP dev server pins localhost to https in the
    # browser and breaks local development until the pin expires.
    import app as app_module
    if app_module.IS_PRODUCTION:
        pytest.skip("running with PRODUCTION=1")
    assert "Strict-Transport-Security" not in client.get("/api/health").headers
