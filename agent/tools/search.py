"""Keyword scoring over a corpus snapshot.

No embeddings and no vector store: a corpus of a few dozen pages is answered
well by term overlap, and a second piece of infrastructure would be a second
thing to explain and a second thing to fail.

Scoring runs over the page TITLE, its PATH and its BODY, because a Context Hub
snapshot carries file contents — so unlike an index-only design this can match
on the text of a page, not just its name.

THREE THINGS A NAIVE VERSION GOT WRONG, all found by the corpus-separation
test rather than by reading the code:

1. **Substring matching is directional.** `"evals" in "the eval gate"` is
   False, so a page was invisible to the question it exists to answer. Fixed by
   tokenizing both sides and comparing light stems.
2. **A single title hit beat three body hits.** With per-field weights alone, a
   page whose *name* contains one query word outranked a page whose text
   answered the whole question — so "Is tracing required in production?" picked
   `deploy-to-production` over the page about tracing. Fixed by scaling for
   coverage: how much of the question a page accounts for.
3. **Repetition inflated scores.** Counting every occurrence let one word
   mentioned often outweigh breadth. Each query term now contributes once, at
   its best field.
"""

from __future__ import annotations

import re

#: Words that carry no signal in a documentation question.
STOPWORDS = frozenset("""
a an and any are as at be been before but by can did do does for from get got
had has have here how i if in into is it its just me must my need needs of on
or our should so some that the their them then there these this to us use
using we what when where which who why will with you your
""".split())

#: Terms the corpora express with a different word than a person asks with.
#: Applied at HALF weight, so a synonym can surface a page but never outrank a
#: literal match.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "schedule": ("cron", "recur", "scheduled"),
    "credential": ("secret", "token", "key", "keyring"),
    "rotate": ("rotation", "revoke", "expiry"),
    "deploy": ("deployment", "release", "pipeline", "promote"),
    "rollback": ("revert", "glass", "recover"),
    "oncall": ("escalation", "page", "rotation", "pager"),
    "incident": ("outage", "postmortem", "review"),
    "eval": ("evaluation", "regression", "dataset"),
    "approval": ("approve", "review", "reviewer"),
    "version": ("pin", "dependency"),
    "trace": ("tracing", "observability", "langsmith"),
    "retry": ("resilience", "timeout", "backoff"),
    "environment": ("staging", "prod", "dev"),
    "require": ("required", "must", "standard", "rule"),
}

W_TITLE, W_PATH, W_BODY = 3.0, 2.0, 1.0

#: Below this, the corpus does not cover the question.
#:
#: Load-bearing for the demo's refusal. Without a threshold, a query the corpus
#: cannot answer still returns its best-scoring page — a real page, entirely
#: irrelevant — and the agent then reads it, finds nothing, and produces a
#: confused half-answer instead of saying it has no coverage.
#:
#: Calibrated against `tests/test_corpus_separation.py`, which asserts both
#: directions: every engineering question clears it in the engineering corpus,
#: and every beat-2 question stays below it in the product corpus. Changing a
#: corpus re-runs that test.
MIN_SCORE = 1.6

_WORD = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """Crude suffix stripping. Enough to make evals/eval and approvals/approval
    the same term; not enough to need a linguistics dependency."""
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> set[str]:
    return {stem(w) for w in _WORD.findall(text.lower())}


def terms(query: str) -> list[str]:
    words = [
        stem(w) for w in _WORD.findall(query.lower())
        if w not in STOPWORDS and len(w) > 2
    ]
    seen: set[str] = set()
    return [w for w in words if not (w in seen or seen.add(w))]


def title_of(path: str, body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.rsplit(".", 1)[0].replace("-", " ")


def score(query: str, path: str, body: str) -> float:
    """Sum each query term's best field weight, scaled by coverage."""
    literal = terms(query)
    if not literal:
        return 0.0

    title_t = tokens(title_of(path, body))
    path_t = tokens(path)
    body_t = tokens(body)

    total, matched = 0.0, 0
    for term in literal:
        # A term scores once, at the strongest field it appears in.
        if term in title_t:
            best = W_TITLE
        elif term in path_t:
            best = W_PATH
        elif term in body_t:
            best = W_BODY
        else:
            # Fall back to synonyms at half weight.
            best = 0.0
            for syn in (stem(s) for s in SYNONYMS.get(term, ())):
                if syn in title_t:
                    best = max(best, W_TITLE * 0.5)
                elif syn in path_t:
                    best = max(best, W_PATH * 0.5)
                elif syn in body_t:
                    best = max(best, W_BODY * 0.5)
            if not best:
                continue
        total += best
        matched += 1

    # Coverage: a page accounting for most of the question beats a page whose
    # name happens to contain one of its words.
    return total * (matched / len(literal))


def rank(query: str, files: dict[str, str], limit: int) -> list[tuple[float, str, str]]:
    """Scored, thresholded, ordered hits: (score, path, title)."""
    hits = [
        (score(query, path, body), path, title_of(path, body))
        for path, body in files.items()
    ]
    hits = [h for h in hits if h[0] >= MIN_SCORE]
    # Sort by score, then path, so equal scores order deterministically —
    # a demo that reorders between runs looks flaky.
    hits.sort(key=lambda h: (-h[0], h[1]))
    return hits[:limit]
