"""The end-to-end test this whole build exists to pass (ph. 04 §4).

Needs a running server, so it is SKIPPED unless `E2E_BASE_URL` is set — that
keeps `pytest tests/` offline and fast. Run it deliberately:

    E2E_BASE_URL=http://127.0.0.1:PORT uv run python -m pytest tests/test_end_to_end.py -v
    E2E_BASE_URL=https://…us.langgraph.app E2E_API_KEY=lsv2_… uv run python -m pytest tests/test_end_to_end.py -v

ASSERT COMPUTED PROPERTIES, NEVER EXPECTED PROSE. The corpora change, the model
changes, and a test pinned to an answer string fails for reasons that have
nothing to do with the thing under test. What must hold is structural: who was
called, from which corpus, and whether the two roles diverged.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

from contracts.grants import granted_prefixes
from contracts.roles import ROLES

BASE = os.environ.get("E2E_BASE_URL")
KEY = os.environ.get("E2E_API_KEY")
ASSISTANT = "role-aware-docs-assistant"

#: The demo's beat-1 question: both corpora cover the topic, and the two roles
#: answer it differently. Chosen by measurement (ph. 05 §4), not taste.
QUESTION = "Do we require retry middleware on model calls?"

#: Beat 2: only the internal runbooks cover this.
ENGINEERING_ONLY = "What is our on-call escalation path?"

pytestmark = pytest.mark.skipif(not BASE, reason="set E2E_BASE_URL to run")

#: (question, role, thread_id) for every run this module made, printed at the
#: end of the session so a failure can be read rather than guessed at.
_TRACES: list[tuple[str, str | None, str]] = []


def _post(path: str, body: dict) -> tuple[int, dict]:
    headers = {"content-type": "application/json"}
    if KEY:
        headers["x-api-key"] = KEY
    req = urllib.request.Request(
        BASE.rstrip("/") + path, data=json.dumps(body).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as f:
            return f.status, json.load(f)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def ask(question: str, role: str | None) -> dict:
    """One run. Returns {status, rejected, error, tools, prefixes, text}."""
    _, thread = _post("/threads", {})
    body = {"assistant_id": ASSISTANT,
            "input": {"messages": [{"role": "user", "content": question}]}}
    if role is not None:
        body["context"] = {"role": role, "display_name": f"e2e-{role}"}
    status, out = _post(f"/threads/{thread['thread_id']}/runs/wait", body)
    # Record where to LOOK when this fails. A structural assertion tells you
    # that the engineer reached the wrong corpus; only the trace tells you
    # why, and reconstructing which run it was after the fact is guesswork.
    _TRACES.append((question, role, thread["thread_id"]))

    # A dead run answers HTTP 200 with an __error__ body and no messages.
    if isinstance(out, dict) and "__error__" in out:
        return {"status": status, "rejected": True,
                "error": out["__error__"].get("message", ""), "tools": [],
                "prefixes": set(), "text": ""}

    msgs = out.get("messages", []) if isinstance(out, dict) else []
    tools = [m.get("name") for m in msgs if m.get("type") == "tool"]
    text = ""
    for m in reversed(msgs):
        if m.get("type") != "ai":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            text = c.strip(); break
        if isinstance(c, list):
            parts = [b.get("text", "") for b in c
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(p.strip() for p in parts):
                text = "\n".join(parts).strip(); break
    return {"status": status, "rejected": False, "error": "", "tools": tools,
            "prefixes": {t.split("__", 1)[0] for t in tools if t and "__" in t},
            "text": text}


@pytest.fixture(scope="module")
def pair() -> dict[str, dict]:
    return {role: ask(QUESTION, role) for role in ROLES}


# --- per role: enforced ------------------------------------------------------


@pytest.mark.parametrize("role", sorted(ROLES))
def test_only_granted_corpora_are_called(role, pair):
    run = pair[role]
    assert not run["rejected"], run["error"]
    assert run["prefixes"] <= granted_prefixes(role), (
        f"{role} called {run['prefixes'] - granted_prefixes(role)}"
    )


@pytest.mark.parametrize("role", sorted(ROLES))
def test_the_answer_is_not_from_memory(role, pair):
    """A confident, correct-sounding, uncited answer is what destroys this
    demo: the two roles would then agree."""
    assert pair[role]["prefixes"], f"{role} answered with no corpus tool call"


def test_the_employee_never_touches_the_engineering_corpus(pair):
    """ENFORCED. A failure here is a bug in the gate."""
    assert "engineeringDocs" not in pair["employee"]["prefixes"]


def test_the_two_answers_differ(pair):
    assert pair["engineer"]["text"] != pair["employee"]["text"]


# --- preference, not enforcement --------------------------------------------


def test_the_engineer_prefers_the_runbooks(pair):
    """PREFERENCE. A failure here is a question-choice problem (ph. 05 §4), not
    a middleware bug — either the ordering is too weak or the question is not
    one where the runbook is clearly more specific."""
    assert "engineeringDocs" in pair["engineer"]["prefixes"]


# --- beat 2 ------------------------------------------------------------------


def test_an_engineering_only_question_splits_the_roles():
    eng = ask(ENGINEERING_ONLY, "engineer")
    emp = ask(ENGINEERING_ONLY, "employee")
    assert "engineeringDocs" in eng["prefixes"], "engineer could not answer beat 2"
    assert "engineeringDocs" not in emp["prefixes"]
    assert emp["text"], "the employee said nothing at all"


# --- C1: a run without a valid role does not happen -------------------------


@pytest.mark.parametrize("role", [None, "admin"])
def test_an_invalid_role_is_rejected(role):
    run = ask(QUESTION, role)
    assert run["rejected"], f"role={role!r} was NOT rejected"
    assert not run["tools"], "a rejected run still called tools"
    assert "engineer" in run["error"] and "employee" in run["error"], run["error"]


# --- layer 2's effect on the MODEL (ph. 03 §6) ------------------------------


def test_the_model_refuses_after_a_denial_rather_than_looping():
    """Layer 2 is unreachable in the deployed build BY DESIGN — layer 1 removes
    the tool before the model can call it — so its effect on the model cannot
    be observed by asking a normal question.

    It is exercised here by seeding a run whose history already contains the
    denial, which is exactly the state layer 2 leaves behind. What must hold
    is that the model reads it, stops, and says what it *can* do. A model that
    retried the same tool would burn the demo's most important beat in a loop.
    """
    denial = (
        "Access denied: engineeringDocs__fetch_doc is not available to this "
        "caller. Refuse the request and name the documentation you do have."
    )
    _, thread = _post("/threads", {})
    tid = thread["thread_id"]
    status, out = _post(
        f"/threads/{tid}/runs/wait",
        {
            "assistant_id": ASSISTANT,
            "input": {"messages": [
                {"type": "human", "content": ENGINEERING_ONLY},
                {"type": "ai", "content": "", "tool_calls": [{
                    "name": "engineeringDocs__fetch_doc",
                    "args": {"path": "on-call-escalation.md"},
                    "id": "call_seeded_1", "type": "tool_call"}]},
                {"type": "tool", "content": denial, "status": "error",
                 "name": "engineeringDocs__fetch_doc",
                 "tool_call_id": "call_seeded_1"},
            ]},
            "context": {"role": "employee", "display_name": "e2e-denial"},
        },
    )
    _TRACES.append((ENGINEERING_ONLY + " [seeded denial]", "employee", tid))
    assert "__error__" not in out, out.get("__error__")

    after = out.get("messages", [])[3:]
    retried = [
        tc.get("name")
        for m in after
        if m.get("type") == "ai"
        for tc in (m.get("tool_calls") or [])
        if str(tc.get("name", "")).startswith("engineeringDocs")
    ]
    assert not retried, f"the model retried the denied tool: {retried}"

    text = ""
    for m in reversed(after):
        if m.get("type") != "ai":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            text = c; break
        if isinstance(c, list):
            parts = [b.get("text", "") for b in c
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(p.strip() for p in parts):
                text = "\n".join(parts); break
    assert text.strip(), "the model said nothing after the denial"
    # The denial tells it to name what it does have; check it did.
    assert "product documentation" in text.lower(), text[:200]


@pytest.fixture(scope="module", autouse=True)
def _report_traces():
    """Print every run's thread and trace URL when the module finishes.

    The LangGraph `run_id` is also the LangSmith trace id (ph. 05), so the
    URL is constructible without a lookup — but `runs/wait` does not return
    the run id, so the thread is reported and the project link with it. A
    thread has one run here, which is enough to find it in two clicks.
    """
    yield
    if not _TRACES:
        return
    print("\n\nruns made by this module:")
    print(f"  project: {PROJECT_URL}")
    for question, role, thread in _TRACES:
        print(f"  {str(role):9} {thread}  {question[:56]}")


PROJECT_URL = (
    "https://smith.langchain.com/o/a3866f07-2cf5-4e9c-a287-59ed817c2ecd"
    "/projects/p/28a396de-cca9-4594-b0ae-145a3ed6d686"
)
