"""Offline screen for demo-question candidates (ph. 05 §4).

A SCREEN, NOT A VERDICT. Scoring tells you whether a corpus has a page that
*looks* relevant. It cannot tell you whether that page *answers* the question.
Phase 05 learned this the expensive way: "How do I deploy a managed deep
agent?" scored as a clean beat 1 here and produced a double refusal live,
because both corpora returned a page above MIN_SCORE and neither page covered
managed deep agents at all.

So the workflow is: score here (seconds, eliminates most candidates), then run
the survivors against the deployment one identity at a time and READ THE
ANSWERS, then write one into the script.

    uv run python -m tests.score_candidates
    uv run python -m tests.score_candidates "some other question"

Classification, from the two corpora's top scores:

    beat 1   both corpora clear MIN_SCORE  -> same question, different answers
    beat 2   only engineeringDocs clears   -> the employee must refuse
    dead     neither clears                -> double refusal, unusable
    inverted only productDocs clears       -> the engineer has nothing extra
"""

from __future__ import annotations

import asyncio
import os
import sys

from tools.search import MIN_SCORE, rank

#: Candidates to screen. Keep the failures: each one records a shape that
#: looked plausible and was not, and re-adding it is how a regression is found.
CANDIDATES = [
    # --- beat 1 hopefuls: both corpora have something to say -----------------
    "Do we require retry middleware on model calls?",
    "Should I turn on tracing in production?",
    "How do I handle errors when a model call fails?",
    "What should I do before deploying an agent to production?",
    "How should agent code be structured and reviewed?",
    "How do I write documentation for an agent?",
    "How do I evaluate whether my agent is working?",
    "What timeout should I use for a model call?",
    # --- beat 2 hopefuls: internal only --------------------------------------
    "What is our on-call escalation path?",
    "How do I rotate a credential?",
    "What is the break-glass procedure?",
    "Who approves a production deploy?",
    "What environments do we have?",
    "How do I pin dependency versions?",
    # --- known dead: kept as regression markers ------------------------------
    "How do I deploy a managed deep agent?",
]


async def corpora() -> dict[str, dict[str, str]]:
    """Both corpora, pulled once. Uses the local dev credential."""
    from langsmith import AsyncClient

    from contracts.grants import CORPORA, repo_and_slug

    key = os.environ.get("MDA_DEV_CONTEXT_HUB_CORPUS") or os.environ["LANGSMITH_API_KEY"]
    client = AsyncClient(api_key=key)
    out: dict[str, dict[str, str]] = {}
    for prefix in CORPORA:
        repo, _ = repo_and_slug(prefix)
        snap = await client.pull_agent(repo)
        out[prefix] = {p: f.content for p, f in snap.files.items()}
    return out


def top(query: str, files: dict[str, str]) -> tuple[float, str]:
    hits = rank(query, files, 1)
    return (hits[0][0], hits[0][1]) if hits else (0.0, "—")


def classify(prod: float, eng: float) -> str:
    if prod >= MIN_SCORE and eng >= MIN_SCORE:
        return "beat 1"
    if eng >= MIN_SCORE:
        return "beat 2"
    if prod >= MIN_SCORE:
        return "inverted"
    return "DEAD"


async def main() -> int:
    questions = sys.argv[1:] or CANDIDATES
    files = await corpora()
    prod, eng = files["productDocs"], files["engineeringDocs"]

    print(f"MIN_SCORE = {MIN_SCORE}\n")
    print(f"{'verdict':9} {'prod':>5} {'eng':>5}  question")
    print("-" * 100)
    rows = []
    for q in questions:
        ps, pp = top(q, prod)
        es, ep = top(q, eng)
        verdict = classify(ps, es)
        rows.append((verdict, q, ps, pp, es, ep))
        print(f"{verdict:9} {ps:5.2f} {es:5.2f}  {q}")

    print("\ntop page per corpus (the screen's real output — a page that scores")
    print("is not a page that answers; confirm live before scripting either)\n")
    for verdict, q, ps, pp, es, ep in rows:
        if verdict == "DEAD":
            continue
        print(f"  {q}")
        print(f"      productDocs      {ps:5.2f}  {pp}")
        print(f"      engineeringDocs  {es:5.2f}  {ep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
