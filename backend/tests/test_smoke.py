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


# ── Reader windowing (/api/works/<id>) ───────────────────────────────────────
#
# Large works are returned a page at a time. The properties that matter are
# that the pages abut exactly — a gap silently swallows text the reader will
# never see — and that a small work still arrives whole.

@pytest.fixture
def paging_client(client):
    """A client with the 30/min cap lifted, for tests that walk a whole work.

    Paging through Augustine's Sermons is dozens of requests from one address,
    which is precisely what the limiter exists to stop. Lifted only inside
    these tests, and restored afterwards, so the default `client` fixture
    still exercises the limited path everywhere else.
    """
    import app as app_module
    app_module.limiter.enabled = False
    try:
        yield client
    finally:
        app_module.limiter.enabled = True


@pytest.fixture(scope="module")
def big_work_id(client):
    """A work large enough that the endpoint must window it."""
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        row = conn.execute("""
            SELECT work_id FROM passages
            GROUP BY work_id
            HAVING SUM(LENGTH(text)) > ?
            ORDER BY SUM(LENGTH(text)) DESC LIMIT 1
        """, (app_module.WORK_FULL_BYTES,)).fetchone()
    finally:
        conn.close()
    if row is None:
        pytest.skip("no work large enough to be windowed")
    return row[0]


def test_small_work_comes_back_complete(client):
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        row = conn.execute("""
            SELECT work_id FROM passages
            GROUP BY work_id
            HAVING SUM(LENGTH(text)) <= ?
            ORDER BY work_id LIMIT 1
        """, (app_module.WORK_FULL_BYTES,)).fetchone()
    finally:
        conn.close()
    if row is None:
        pytest.skip("no small work in the corpus")

    body = client.get(f"/api/works/{row[0]}").get_json()
    assert body["complete"] is True
    assert body["has_prev"] is False and body["has_next"] is False
    assert len(body["passages"]) == body["total_passages"]
    # A complete work needs no separate chapter index — it has every header.
    assert body["chapters"] == []


def test_large_work_is_windowed(client, big_work_id):
    import app as app_module
    body = client.get(f"/api/works/{big_work_id}").get_json()
    assert body["complete"] is False
    assert body["offset"] == 0 and body["has_next"] is True
    assert 0 < len(body["passages"]) < body["total_passages"]
    # The chapter index still covers the whole work so navigation never waits.
    assert len(body["chapters"]) >= 1
    assert body["chapters"][0]["index"] == 0
    assert max(c["index"] for c in body["chapters"]) < body["total_passages"]
    # One passage may legitimately exceed the budget on its own; two must not.
    if len(body["passages"]) > 1:
        size = sum(len(p["text"] or "") for p in body["passages"])
        assert size <= app_module.WORK_WINDOW_BYTES * 1.5


def test_windows_tile_the_work_without_gaps(paging_client, big_work_id):
    """Walking forward must reproduce the work exactly — no gap, no repeat."""
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        expected = [r[0] for r in conn.execute(
            "SELECT id FROM passages WHERE work_id = ? ORDER BY id", (big_work_id,)
        )]
    finally:
        conn.close()

    seen, offset = [], 0
    for _ in range(len(expected) + 1):
        body = paging_client.get(f"/api/works/{big_work_id}?offset={offset}").get_json()
        seen += [p["id"] for p in body["passages"]]
        if not body["has_next"]:
            break
        offset = body["offset"] + len(body["passages"])
    assert seen == expected


def test_backward_windows_abut_the_one_they_precede(paging_client, big_work_id):
    body = paging_client.get(f"/api/works/{big_work_id}?offset=0").get_json()
    boundary = len(body["passages"])
    nxt = paging_client.get(f"/api/works/{big_work_id}?offset={boundary}").get_json()
    prev = paging_client.get(f"/api/works/{big_work_id}?before={boundary}").get_json()
    # `before` ends exactly where the window at `boundary` begins.
    assert prev["offset"] + len(prev["passages"]) == nxt["offset"] == boundary


def test_around_centres_the_window_on_the_passage(paging_client, big_work_id):
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        ids = [r[0] for r in conn.execute(
            "SELECT id FROM passages WHERE work_id = ? ORDER BY id", (big_work_id,)
        )]
    finally:
        conn.close()
    target = ids[len(ids) // 2]

    body = paging_client.get(f"/api/works/{big_work_id}?around={target}").get_json()
    # The whole point: the passage the reader clicked is in the first response.
    assert target in [p["id"] for p in body["passages"]]
    assert body["has_prev"] is True


def test_unknown_around_falls_back_to_the_opening_window(paging_client, big_work_id):
    # A stale or wrong passage id must still render the work, not 500.
    body = paging_client.get(f"/api/works/{big_work_id}?around=999999999").get_json()
    assert body["offset"] == 0
    assert body["passages"]


# ── Passage kind ─────────────────────────────────────────────────────────────

def test_writing_index_is_derived_and_is_the_minority():
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    finally:
        conn.close()
    writings = len(app_module.WRITING_PASSAGE_IDS)
    # Derived from scripture_index rather than a stored column — if the catena
    # pipeline ever stops writing those rows this flips and search silently
    # starts calling every commentary a "writing".
    assert 0 < writings < total
    assert writings / total < 0.25


def test_passage_kind_labels_both_shapes():
    import app as app_module
    conn = app_module.get_db_connection()
    try:
        commentary = conn.execute(
            "SELECT passage_id FROM scripture_index LIMIT 1"
        ).fetchone()
        writing = conn.execute("""
            SELECT p.id FROM passages p
            LEFT JOIN (SELECT DISTINCT passage_id FROM scripture_index) si
                   ON si.passage_id = p.id
            WHERE si.passage_id IS NULL LIMIT 1
        """).fetchone()
    finally:
        conn.close()
    if commentary is None or writing is None:
        pytest.skip("corpus has only one kind of passage")
    assert app_module.passage_kind(commentary[0]) == "commentary"
    assert app_module.passage_kind(writing[0]) == "writing"


def test_search_results_carry_a_kind(client):
    # The results filter is driven entirely by this field; without it the
    # facet silently disappears from the UI.
    body = client.get("/api/search?q=hardship").get_json()
    results = body.get("results", [])
    if not results:
        pytest.skip("search degraded (no API keys configured)")
    assert all(r.get("kind") in ("writing", "commentary") for r in results)
