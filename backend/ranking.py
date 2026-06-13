"""Result ranking — Reciprocal Rank Fusion + per-work/per-author diversification.

Pure-Python: takes ranked hit lists and lookup dicts, returns ranked passage
ids. No DB, no embeddings, no Flask — easy to unit-test, easy to reason about.
"""


# RRF signal weights — tuning knobs. Vector leads because it matches *meaning*,
# not just surface words; FTS keeps exact-term precision; title is a gentle
# nudge toward whole treatises. Raise VECTOR if results feel too literal, raise
# FTS if they feel too fuzzy / off-topic.
RRF_WEIGHT_VECTOR = 1.3
RRF_WEIGHT_FTS = 1.0
RRF_WEIGHT_TITLE = 0.5


# A topic search across the whole corpus reads better with variety than with
# ten near-identical snippets from one commentary (or one prolific author), so
# cap how many passages any single work / author may contribute to a result
# set. The author cap is looser — one Father can legitimately own several
# relevant works.
DIVERSITY_CAP_PER_WORK = 3
DIVERSITY_CAP_PER_AUTHOR = 6


def rrf_accumulate(fused, hits, weight=1.0, k=60):
    """Add one ranked hit list to the fused scores via reciprocal rank fusion.

    RRF is scale-free (uses rank, not raw score), so vector cosine, FTS bm25 and
    title-match scores fuse without normalization. ``weight`` tunes a signal's
    pull. Mutates ``fused`` in place.
    """
    for rank, (pid, _score) in enumerate(hits):
        fused[pid] = fused.get(pid, 0.0) + weight / (k + rank + 1)


def diversify(passage_ids, passage_work, passage_author, limit,
              work_cap=DIVERSITY_CAP_PER_WORK,
              author_cap=DIVERSITY_CAP_PER_AUTHOR):
    """Cap how many passages any single work / author contributes, preserving
    rank order, so one commentary or one prolific Father can't flood the page.

    ``passage_work`` / ``passage_author`` are passage_id -> id lookup dicts
    (built once at module load by the caller).
    """
    out, per_work, per_author = [], {}, {}
    for pid in passage_ids:
        wid = passage_work.get(pid)
        aid = passage_author.get(pid)
        if per_work.get(wid, 0) >= work_cap or per_author.get(aid, 0) >= author_cap:
            continue
        per_work[wid] = per_work.get(wid, 0) + 1
        per_author[aid] = per_author.get(aid, 0) + 1
        out.append(pid)
        if len(out) >= limit:
            break
    return out
