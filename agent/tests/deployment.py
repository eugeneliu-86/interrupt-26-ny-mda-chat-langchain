"""Talking to the deployed agent, and finding the trace afterwards (ph. 05).

Shared by the verification harness (§2), the question picker (§4) and anything
else that needs a real run. Not a test module — `pytest` collects nothing here.

THE ONE FACT THAT MAKES THIS CHEAP. The LangGraph `run_id` returned by
`POST /threads/{id}/runs` **is** the LangSmith root run id *and* its trace id.
Measured, not assumed: a run created here was read back with
`Client.read_run(run_id)` and came back as the root `role-aware-docs-assistant`
run with `trace_id == run_id`.

So a trace URL is a string built from ids already in hand — no polling
LangSmith to discover which run belongs to which request, and no race between
the run finishing and the trace being queryable. Phase 06 relies on the same
fact to build its "view trace" link inside the proxy.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get(
    "E2E_BASE_URL",
    "https://role-aware-docs-assistant-679d6573475f558188a07a13bc2b152c.us.langgraph.app",
).rstrip("/")
KEY = os.environ.get("E2E_API_KEY") or os.environ.get("LANGSMITH_API_KEY", "")
ASSISTANT = "role-aware-docs-assistant"

WORKSPACE = "a3866f07-2cf5-4e9c-a287-59ed817c2ecd"
PROJECT_ID = "28a396de-cca9-4594-b0ae-145a3ed6d686"
PROJECT_URL = f"https://smith.langchain.com/o/{WORKSPACE}/projects/p/{PROJECT_ID}"


def trace_url(run_id: str) -> str:
    """The LangSmith trace for a LangGraph run id. See the module note."""
    return f"{PROJECT_URL}/r/{run_id}"


def _req(method: str, path: str, body: dict | None = None, key: str | None = None):
    headers = {"content-type": "application/json"}
    k = KEY if key is None else key
    if k:
        headers["x-api-key"] = k
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as f:
            raw = f.read()
            return f.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"detail": raw.decode(errors="replace")[:400]}


def text_of(messages: list[dict]) -> str:
    """The last assistant text.

    `gpt-5.6-luna` returns `content` as a LIST of blocks — reasoning, function
    calls, then text. Reading it as a string yields "" and looks like an agent
    that said nothing. Phase 06 renders the same shape.
    """
    for m in reversed(messages):
        if m.get("type") != "ai":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()
        if isinstance(c, list):
            parts = [
                b.get("text", "")
                for b in c
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            if any(p.strip() for p in parts):
                return "\n".join(p for p in parts if p.strip()).strip()
    return ""


def ask(
    question: str,
    role: str | None,
    *,
    context: dict | None = None,
    key: str | None = None,
) -> dict:
    """One run against the deployment, with its trace URL.

    `role` builds the usual context; `context` overrides it wholesale so a
    caller can send a malformed one. Returns a dict that is safe to print.
    """
    status, thread = _req("POST", "/threads", {}, key=key)
    if status >= 400:
        return {
            "status": status, "rejected": True, "error": json.dumps(thread)[:300],
            "tools": [], "calls": [], "prefixes": set(), "pages": set(),
            "text": "", "run_id": "", "trace": "", "denials": 0,
        }

    body: dict = {
        "assistant_id": ASSISTANT,
        "input": {"messages": [{"role": "user", "content": question}]},
    }
    if context is not None:
        body["context"] = context
    elif role is not None:
        body["context"] = {"role": role, "display_name": f"verify-{role}"}

    tid = thread["thread_id"]
    status, run = _req("POST", f"/threads/{tid}/runs", body, key=key)
    if status >= 400:
        return {
            "status": status, "rejected": True, "error": json.dumps(run)[:300],
            "tools": [], "calls": [], "prefixes": set(), "pages": set(),
            "text": "", "run_id": "", "trace": "", "denials": 0,
        }

    rid = run["run_id"]
    status, out = _req("GET", f"/threads/{tid}/runs/{rid}/join", key=key)
    result = {
        "status": status,
        "run_id": rid,
        "trace": trace_url(rid),
        "thread_id": tid,
        "rejected": False,
        "error": "",
        "tools": [],
        "calls": [],
        "prefixes": set(),
        "pages": set(),
        "text": "",
        "denials": 0,
    }

    # A DEAD RUN ANSWERS HTTP 200. `{"__error__": …}` with no messages is how a
    # rejected or crashed run comes back — status alone tells you nothing.
    if isinstance(out, dict) and "__error__" in out:
        result["rejected"] = True
        result["error"] = out["__error__"].get("message", "")
        return result

    msgs = out.get("messages", []) if isinstance(out, dict) else []
    tools = [m.get("name") for m in msgs if m.get("type") == "tool"]
    result["tools"] = tools
    result["prefixes"] = {t.split("__", 1)[0] for t in tools if t and "__" in t}
    result["text"] = text_of(msgs)

    # WHICH PAGE ANSWERED — the arguments, not just the tool names. Criterion 3
    # of ph. 05 §4 is "different paths cited", and a tool name cannot show
    # that. Arguments live on the AI message's `tool_calls`, never on the
    # ToolMessage, so they are read from the calling side.
    calls: list[tuple[str, dict]] = []
    for m in msgs:
        if m.get("type") != "ai":
            continue
        for tc in m.get("tool_calls") or []:
            calls.append((tc.get("name", ""), tc.get("args") or {}))
    result["calls"] = calls
    result["pages"] = {
        f"{name.split('__', 1)[0]}/{args['path']}"
        for name, args in calls
        if name.endswith("__fetch_doc") and isinstance(args.get("path"), str)
    }
    # Layer 2 (ph. 03 §6) returns a ToolMessage whose content starts this way.
    result["denials"] = sum(
        1
        for m in msgs
        if m.get("type") == "tool"
        and isinstance(m.get("content"), str)
        and m["content"].startswith("Access denied")
    )
    return result
