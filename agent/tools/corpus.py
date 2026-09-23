"""The corpus tools: one search/fetch pair per corpus (C4, C6).

Each pair is built by a factory that CLOSES OVER its corpus prefix. The corpus
is never a tool parameter, so a tool cannot be asked for another corpus — not
by the model, not by a crafted path, not by prompt injection. Paths are keys in
a pulled dict rather than filesystem or URL paths, so traversal is meaningless.

Credentials come from the `context-hub-corpus` connection, resolved inside the
run. Nothing ambient, nothing personal, nothing in the repo.
"""

from __future__ import annotations

import os
import time
from typing import Any

from langchain.tools import tool
from managed_deepagents import connections

from contracts.grants import CORPUS_BLURB, repo_and_slug
from tools.search import rank, title_of

#: Seconds a pulled snapshot is reused.
#:
#: Short on purpose. Rotating or revoking the corpus credential takes effect on
#: the next PULL, not the next call — a cached snapshot keeps serving until it
#: expires. Sixty seconds keeps the rotation demo snappy while still collapsing
#: the many pulls a single multi-step answer would otherwise make.
CACHE_TTL_SECONDS = float(os.environ.get("CORPUS_CACHE_TTL", "60"))

#: prefix -> (expires_at, commit_hash, {path: content})
_CACHE: dict[str, tuple[float, str, dict[str, str]]] = {}


async def snapshot(prefix: str) -> tuple[str, dict[str, str]]:
    """Pull one corpus, or serve it from the short-lived cache.

    A failed REFRESH keeps serving the previous snapshot: a demo running on a
    minute-old corpus is fine, a demo that goes silent because one pull
    hiccuped is not. A failed FIRST pull raises, because there is nothing
    truthful to answer with.
    """
    now = time.monotonic()
    cached = _CACHE.get(prefix)
    if cached and cached[0] > now:
        return cached[1], cached[2]

    repo, slug = repo_and_slug(prefix)
    try:
        # Imported here so the module imports cleanly without langsmith present
        # (the offline tests build tools against a fake snapshot).
        from langsmith import AsyncClient

        key = await connections.get(slug, {"type": "agent"})
        client = AsyncClient(api_key=key)
        snap = await client.pull_agent(repo)
        files = {p: f.content for p, f in snap.files.items()}
        _CACHE[prefix] = (now + CACHE_TTL_SECONDS, snap.commit_hash, files)
        return snap.commit_hash, files
    except Exception:
        if cached:
            return cached[1], cached[2]
        raise


def stamp_provenance(prefix: str, commit_hash: str) -> None:
    """Record which corpus commit answered, on THIS TOOL'S run (C9, ph. 02 §9).

    WHY THE TOOL SPAN AND NOT THE ROOT RUN. A middleware write to the run tree
    does not reach the root run — measured in v3, where a `granted` key never
    appeared and the middleware that wrote it was deleted. A tool, though, is
    its own run, and writing to the current run tree from inside the tool lands
    on that tool's span, which is exactly where a reader is already looking
    when they ask "which document answered this?".

    WHY NOT PUT IT IN THE RETURN STRING. That text goes to the model, which
    would then have a commit hash it might quote at the user, and the corpus
    content would gain a field nobody wrote. Metadata is read by people and
    ignored by the model, which is the correct audience for a provenance
    stamp.

    Best-effort by design: a tracing failure must never break an answer.
    """
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is not None:
            run.add_metadata({f"{prefix}_commit": commit_hash})
    except Exception:
        pass


def normalize(path: str) -> str:
    """A page key from whatever the model passed.

    Accepts `deploy-to-production`, `/deploy-to-production`, and
    `deploy-to-production.md` identically.
    """
    cleaned = path.strip().strip("/")
    return cleaned if cleaned.endswith(".md") else f"{cleaned}.md"


#: What a tool returns when the corpus cannot be reached at all.
#:
#: WHY THE TOOLS SWALLOW THIS. A raising tool does not become a `ToolMessage`
#: here: LangGraph's tool-error handling re-raised a `LangSmithError` from the
#: pull, the run died, and `/runs/wait` answered **HTTP 200** with an
#: `{"__error__": …}` body and no messages at all. On stage that is a silent
#: agent — the worst possible failure shape, and indistinguishable from the
#: model having nothing to say.
#:
#: So the tools convert an unreachable corpus into a readable result the model
#: can relay. `snapshot()` still raises, so the cause stays visible in the
#: trace and in the logs.
_UNREACHABLE = (
    "This corpus is temporarily unreachable ({reason}). Tell the user the "
    "documentation cannot be reached right now, and do not answer from memory."
)


def corpus_tools(prefix: str) -> list[Any]:
    """Build the (search, fetch) pair for one corpus."""
    blurb = CORPUS_BLURB[prefix]

    @tool(f"{prefix}__search_docs")
    async def search_docs(query: str, limit: int = 8) -> str:
        """Search this corpus by keyword and return matching page titles and paths.

        Results are titles and paths only. Fetch a page before making any claim
        from it.
        """
        try:
            commit, files = await snapshot(prefix)
        except Exception as exc:
            return _UNREACHABLE.format(reason=type(exc).__name__)
        stamp_provenance(prefix, commit)
        hits = rank(query, files, limit)
        if not hits:
            return (f"No pages in this corpus match that query. "
                    f"This corpus covers {blurb}.")
        lines = [f"{len(hits)} match(es) in {blurb}:"]
        lines += [f"- {title}  ({path})" for _, path, title in hits]
        return "\n".join(lines)

    @tool(f"{prefix}__fetch_doc")
    async def fetch_doc(path: str) -> str:
        """Fetch one page from this corpus as Markdown.

        `path` is a page name as returned by the matching search tool, with or
        without a leading slash or a `.md` suffix.
        """
        try:
            commit, files = await snapshot(prefix)
        except Exception as exc:
            return _UNREACHABLE.format(reason=type(exc).__name__)
        stamp_provenance(prefix, commit)
        key = normalize(path)
        body = files.get(key)
        if body is None:
            # Distinguish "no such page here" from "wrong corpus": the right
            # next action differs, and the model can only choose if it is told.
            available = ", ".join(sorted(files)[:12])
            return (f"'{path}' is not a page in this corpus. "
                    f"This corpus covers {blurb}. Pages: {available}")
        return body

    search_docs.description = (
        f"Search {blurb} by keyword. Returns matching page titles and paths. "
        "Fetch a page before making any claim from it."
    )
    fetch_doc.description = f"Fetch one page from {blurb} as Markdown."
    return [search_docs, fetch_doc]


TOOLS = [*corpus_tools("productDocs"), *corpus_tools("engineeringDocs")]
