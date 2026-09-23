"""The corpus tools, tested offline against a fake snapshot.

No network, no credential, no LLM. Everything these tools do apart from the
pull itself is a pure function of a snapshot, so it can be asserted exactly:
which tools exist, what they are called, what they say when a corpus has no
coverage, and that a corpus boundary cannot be crossed by a crafted path.
"""

from __future__ import annotations

import asyncio

import pytest

from contracts.grants import CORPORA, GRANTS
from tools import corpus as corpus_mod
from tools.corpus import TOOLS, normalize

#: Captured before the autouse fixture replaces it, so the caching tests can
#: exercise the real implementation rather than the fake.
REAL_SNAPSHOT = corpus_mod.snapshot

FAKE = {
    "productDocs": {
        "middleware.md": "# Middleware\n\nHooks that wrap model and tool calls, "
                         "including retry and fallback behaviour.\n",
        "langgraph.md": "# LangGraph\n\nStateful agents as graphs.\n",
    },
    "engineeringDocs": {
        "resilience-standards.md": "# Resilience standards\n\nRetry middleware is "
                                   "required on every model call.\n",
        "on-call-escalation.md": "# On-call and escalation\n\nThe rotation is "
                                 "platform-agents-oncall, tiers T1 to T3.\n",
    },
}


@pytest.fixture(autouse=True)
def fake_snapshot(monkeypatch):
    """Serve a fixed snapshot, and record which corpus each call asked for."""
    asked: list[str] = []

    async def _snapshot(prefix: str):
        asked.append(prefix)
        return "fakecommit", FAKE[prefix]

    monkeypatch.setattr(corpus_mod, "snapshot", _snapshot)
    corpus_mod._CACHE.clear()
    return asked


def tool_by_name(name: str):
    for t in TOOLS:
        if t.name == name:
            return t
    raise AssertionError(f"no tool named {name}; have {[t.name for t in TOOLS]}")


def call(tool, **kwargs) -> str:
    return asyncio.run(tool.ainvoke(kwargs))


# --- shape -------------------------------------------------------------------

def test_one_search_and_fetch_pair_per_corpus():
    assert sorted(t.name for t in TOOLS) == sorted(
        f"{p}__{verb}" for p in CORPORA for verb in ("search_docs", "fetch_doc")
    )


def test_every_granted_prefix_has_tools():
    """Catches a renamed prefix before it silently ungates a corpus in ph. 03."""
    loaded = {t.name.split("__", 1)[0] for t in TOOLS}
    granted = set().union(*GRANTS.values())
    assert granted <= loaded, f"granted but no tool: {granted - loaded}"
    assert loaded <= set(CORPORA), f"tool prefix not in CORPORA: {loaded - set(CORPORA)}"


def test_each_description_names_only_its_own_corpus():
    """A description mentioning the other corpus would tell an employee-role
    model that internal runbooks exist (C7)."""
    for t in TOOLS:
        prefix = t.name.split("__", 1)[0]
        others = [p for p in CORPORA if p != prefix]
        for other in others:
            from contracts.grants import CORPUS_BLURB
            assert CORPUS_BLURB[other] not in t.description, (
                f"{t.name} description mentions {other}"
            )


def test_no_tool_takes_a_role_repo_or_scope_parameter():
    for t in TOOLS:
        fields = set(t.args_schema.model_json_schema().get("properties", {}))
        assert not fields & {"role", "repo", "corpus", "scope", "identity"}, (
            f"{t.name} exposes {fields}"
        )


# --- search ------------------------------------------------------------------

def test_search_returns_hits_from_its_own_corpus():
    out = call(tool_by_name("engineeringDocs__search_docs"),
               query="What is our on-call escalation path?")
    assert "on-call-escalation.md" in out


def test_search_says_so_when_the_corpus_has_no_coverage():
    """The refusal the demo depends on: no weak hit, an explicit statement."""
    out = call(tool_by_name("productDocs__search_docs"),
               query="What is our on-call escalation path?")
    assert "No pages in this corpus match" in out
    assert "product documentation" in out


def test_search_asks_only_its_own_corpus(fake_snapshot):
    call(tool_by_name("productDocs__search_docs"), query="middleware")
    assert fake_snapshot == ["productDocs"]


# --- fetch -------------------------------------------------------------------

@pytest.mark.parametrize("given", [
    "resilience-standards", "/resilience-standards", "resilience-standards.md",
    "/resilience-standards.md", "  resilience-standards  ",
])
def test_fetch_accepts_path_variants(given):
    out = call(tool_by_name("engineeringDocs__fetch_doc"), path=given)
    assert out.startswith("# Resilience standards")


def test_normalize_is_total():
    assert normalize("a") == "a.md"
    assert normalize("/a.md") == "a.md"
    assert normalize(" /a ") == "a.md"


def test_fetch_of_a_missing_page_is_distinguishable_from_no_coverage():
    out = call(tool_by_name("productDocs__fetch_doc"), path="nonexistent-thing")
    assert "not a page in this corpus" in out
    assert "Pages:" in out            # tells the model what it could fetch


def test_a_crafted_path_cannot_reach_the_other_corpus(fake_snapshot):
    """Paths are dict keys, not filesystem or URL paths: traversal is a miss."""
    out = call(tool_by_name("engineeringDocs__fetch_doc"),
               path="../product-docs/middleware.md")
    assert "not a page in this corpus" in out
    assert "Middleware" not in out
    assert fake_snapshot == ["engineeringDocs"]   # never pulled the other repo


# --- caching -----------------------------------------------------------------

def test_a_failed_refresh_keeps_serving_the_previous_snapshot(monkeypatch):
    """A demo on a minute-old corpus is fine; one that goes silent is not."""
    monkeypatch.setattr(corpus_mod, "snapshot", REAL_SNAPSHOT)
    monkeypatch.setattr(corpus_mod, "CACHE_TTL_SECONDS", 0.0)
    corpus_mod._CACHE.clear()
    corpus_mod._CACHE["productDocs"] = (
        corpus_mod.time.monotonic() - 1, "stale", {"x.md": "# X\n"}
    )

    async def boom(*_a, **_k):
        raise RuntimeError("pull failed")

    monkeypatch.setattr(corpus_mod.connections, "get", boom)
    commit, files = asyncio.run(REAL_SNAPSHOT("productDocs"))
    assert (commit, files) == ("stale", {"x.md": "# X\n"})


def test_a_failed_first_pull_raises(monkeypatch):
    monkeypatch.setattr(corpus_mod, "snapshot", REAL_SNAPSHOT)
    corpus_mod._CACHE.clear()

    async def boom(*_a, **_k):
        raise RuntimeError("pull failed")

    monkeypatch.setattr(corpus_mod.connections, "get", boom)
    with pytest.raises(RuntimeError):
        asyncio.run(REAL_SNAPSHOT("productDocs"))


# --- an unreachable corpus ---------------------------------------------------

def test_an_unreachable_corpus_returns_a_readable_result_not_an_exception(monkeypatch):
    """A raising tool killed the whole run and `/runs/wait` answered HTTP 200
    with an `__error__` body and no messages — a silent agent. The tools must
    degrade into something the model can say out loud."""
    monkeypatch.setattr(corpus_mod, "snapshot", REAL_SNAPSHOT)
    corpus_mod._CACHE.clear()

    async def boom(*_a, **_k):
        raise RuntimeError("403 Forbidden")

    monkeypatch.setattr(corpus_mod.connections, "get", boom)
    for name in ("productDocs__search_docs", "engineeringDocs__fetch_doc"):
        t = tool_by_name(name)
        out = call(t, **({"query": "anything"} if "search" in name else {"path": "x"}))
        assert "temporarily unreachable" in out, f"{name}: {out!r}"
        assert "do not answer from memory" in out


# --- provenance: which corpus commit answered (ph. 02 §9, C9) ---------------


def test_provenance_lands_on_the_current_run_tree():
    """`stamp_provenance` writes to the tool's OWN span.

    A middleware write to the run tree does not reach the root run — that was
    measured in v3 and the middleware doing it was deleted. A tool is its own
    run, so this write lands where a trace reader is already looking.
    """
    from tools import corpus

    seen: dict[str, str] = {}

    class FakeRun:
        def add_metadata(self, meta):
            seen.update(meta)

    import langsmith.run_helpers as rh

    original = rh.get_current_run_tree
    rh.get_current_run_tree = lambda: FakeRun()
    try:
        corpus.stamp_provenance("engineeringDocs", "abc123")
    finally:
        rh.get_current_run_tree = original

    assert seen == {"engineeringDocs_commit": "abc123"}


def test_provenance_never_breaks_an_answer():
    """Tracing is best-effort. A demo must not go silent because a metadata
    write failed — the answer is the product, the stamp is a convenience."""
    from tools import corpus

    import langsmith.run_helpers as rh

    original = rh.get_current_run_tree

    def boom():
        raise RuntimeError("no run tree here")

    rh.get_current_run_tree = boom
    try:
        corpus.stamp_provenance("productDocs", "deadbeef")  # must not raise
    finally:
        rh.get_current_run_tree = original


def test_provenance_outside_a_run_is_a_no_op():
    from tools import corpus

    import langsmith.run_helpers as rh

    original = rh.get_current_run_tree
    rh.get_current_run_tree = lambda: None
    try:
        corpus.stamp_provenance("productDocs", "deadbeef")
    finally:
        rh.get_current_run_tree = original
