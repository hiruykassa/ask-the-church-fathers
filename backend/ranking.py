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


# The corpus is 94% verse-keyed commentary: 49,757 passages against 3,113
# standalone writings (treatises, letters, sermons, orations). That ratio, not
# the ranking, is why a topical search comes back looking like a stack of Bible
# commentaries — writings do not rank badly, there are simply sixteen times
# fewer of them, so a purely rank-ordered page almost never contains one.
#
# So keep a small floor of writing slots on a page when the candidate pool has
# any. This is deliberately a *floor*, not a quota: it swaps only the weakest
# results, never touches the top of the page, and does nothing at all when the
# ranking already surfaced enough writings or when none matched.
DIVERSITY_WRITING_FLOOR = 2

# …and the floor has to apply to what the reader actually *sees*. Search
# returns up to 100 ranked ids but the UI reveals 15 at a time, so a floor
# measured across the whole list is satisfied by a writing sitting at rank 80
# — which the reader never reaches. Scope it to the first page instead. Keep
# this in step with PAGE_SIZE in src/components/SearchResults.jsx.
DIVERSITY_WRITING_WINDOW = 15


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
              author_cap=DIVERSITY_CAP_PER_AUTHOR,
              writing_ids=None,
              writing_floor=DIVERSITY_WRITING_FLOOR,
              writing_window=DIVERSITY_WRITING_WINDOW):
    """Cap how many passages any single work / author contributes, preserving
    rank order, so one commentary or one prolific Father can't flood the page.

    ``passage_work`` / ``passage_author`` are passage_id -> id lookup dicts
    (built once at module load by the caller).

    ``writing_ids`` is the set of passages that are standalone writings rather
    than verse-keyed commentary. Pass it to enable the writing floor described
    above; omit it and this behaves exactly as it always did.
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

    if not writing_ids or writing_floor <= 0 or not out:
        return out

    return _apply_writing_floor(
        out, passage_ids, writing_ids, passage_work, passage_author,
        per_work, per_author, work_cap, author_cap, writing_floor,
        writing_window,
    )


def _apply_writing_floor(out, ranked, writing_ids, passage_work, passage_author,
                         per_work, per_author, work_cap, author_cap, floor,
                         window):
    """Promote the best missing writings into the weakest slots of page one.

    Two things make this safe. It only ever touches the *bottom* of the first
    page, so the reader's top hits stay exactly as ranked — the change lands
    where a near-duplicate tenth commentary snippet was worth less than the
    first treatise on the subject. And when the promoted writing was already
    further down the list the two are **exchanged**, so the returned list is a
    permutation of the input: nothing is dropped and nothing is duplicated.

    Displacing a result frees its work/author quota, so the caps are re-checked
    as we go and a promotion that would breach them is skipped.
    """
    # Only the first page counts, and only its slots may be swapped: search
    # returns 100 ids but the reader is shown 15.
    page = min(window, len(out)) if window else len(out)
    present = sum(1 for pid in out[:page] if pid in writing_ids)
    if present >= floor:
        return out

    # Candidates are writings anywhere in the ranking that page one is missing
    # — including ones sitting at rank 80, which the reader never reaches.
    on_page = set(out[:page])
    spare = [pid for pid in ranked if pid in writing_ids and pid not in on_page]
    if not spare:
        return out

    result = list(out)
    position = {pid: i for i, pid in enumerate(result)}
    need = floor - present
    cursor = page - 1
    promoted = []  # (slot, pid), collected bottom-up

    for pid in spare:
        if need <= 0:
            break
        # Walk up from the bottom of page one to the weakest commentary hit.
        while cursor >= 0 and result[cursor] in writing_ids:
            cursor -= 1
        if cursor < 0:
            break

        evicted = result[cursor]
        ev_wid, ev_aid = passage_work.get(evicted), passage_author.get(evicted)
        wid, aid = passage_work.get(pid), passage_author.get(pid)
        # An exchange keeps both ids on the list, so the caps cannot be
        # breached; only a true replacement changes the composition.
        exchange = pid in position
        if not exchange and (
                per_work.get(wid, 0) - (1 if wid == ev_wid else 0) >= work_cap
                or per_author.get(aid, 0) - (1 if aid == ev_aid else 0) >= author_cap):
            continue  # this writing would break a cap — try the next one

        if not exchange:
            per_work[ev_wid] = per_work.get(ev_wid, 1) - 1
            per_author[ev_aid] = per_author.get(ev_aid, 1) - 1
            per_work[wid] = per_work.get(wid, 0) + 1
            per_author[aid] = per_author.get(aid, 0) + 1

        promoted.append((cursor, pid))
        cursor -= 1
        need -= 1

    # Slots were found bottom-up but `spare` is in rank order, so pair them the
    # other way round: the best writing takes the highest of the freed slots.
    for slot, pid in zip(sorted(s for s, _ in promoted), [p for _, p in promoted]):
        old = position.get(pid)
        evicted = result[slot]
        result[slot] = pid
        if old is not None:
            # Exchange — the displaced result takes the writing's old place
            # rather than falling off the list entirely.
            result[old] = evicted
            position[evicted] = old
        position[pid] = slot
    return result
