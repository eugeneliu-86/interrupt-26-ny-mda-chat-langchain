"""Can a stranger SEE that MDA handled the auth? (ph. 05 §3)

    uv run python -m tests.verify_auth_visible

The demo's claim is "MDA resolves the credential for you, per run, and it
never touches your repo". Until v7 that was a sentence with no evidence: the
resolution happened — MDA's runtime reads Agent Auth on every await and
caches nothing — but it produced no span at all. A trace showed a tool call
and said nothing about where its credential came from.

Three spans now carry the story, and this asserts all three exist on a real
run, plus the one thing that must NEVER be true: the credential itself
appearing anywhere in the trace.
"""

from __future__ import annotations

import json
import os
import sys

from langsmith import Client

from tests.deployment import KEY, ask

#: The spans that make the auth legible, and what each must prove.
EXPECTED = {
    "reject_unknown_role.before_agent": "layer 0 ran and admitted this role",
    "authorize_tool_surface": "layer 1's decision: granted, withheld, removed",
    "deny_ungranted_tool.awrap_tool_call": "layer 2 saw every tool call",
    "resolve_connection": "MDA fetched the credential from Agent Auth",
}


def main() -> int:
    role = sys.argv[1] if len(sys.argv) > 1 else "employee"
    run = ask("What is our on-call escalation path?", role)
    if run["rejected"]:
        print(f"run died: {run['error']}")
        return 1
    print(f"role={role}  trace={run['trace']}")

    import time

    time.sleep(12)
    c = Client(api_key=KEY)
    root = c.read_run(run["run_id"])
    kids = list(c.list_runs(trace_id=root.trace_id, is_root=False, limit=100))
    names = {k.name for k in kids}

    bad = 0
    print()
    for span, why in EXPECTED.items():
        ok = span in names
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {span:38} {why}")

    # --- layer 1 said what it decided ---------------------------------------
    auth = [k for k in kids if k.name == "authorize_tool_surface"]
    if auth:
        out = auth[0].outputs or {}
        for field in ("granted", "withheld", "preference_order", "removed_tools"):
            ok = field in out
            bad += not ok
            print(f"  [{'PASS' if ok else 'FAIL'}] authorize_tool_surface.{field:16} {out.get(field)}")
    else:
        bad += 1

    # --- the connection span names the connection, not the secret -----------
    conn = [k for k in kids if k.name == "resolve_connection"]
    if conn:
        i, o = conn[0].inputs or {}, conn[0].outputs or {}
        checks = [
            ("names the connection slug", i.get("connection") == "context-hub-corpus"),
            ("says the owner is the agent", i.get("owner") == "agent"),
            ("credits MDA Agent Auth", o.get("source") == "MDA Agent Auth"),
            ("records no credential", o.get("credential") == "<never recorded>"),
        ]
        for label, ok in checks:
            bad += not ok
            print(f"  [{'PASS' if ok else 'FAIL'}] resolve_connection {label}")
    else:
        bad += 1

    # --- THE ONE THAT MATTERS ------------------------------------------------
    # A span that proves the credential was resolved must never contain it.
    # This walks the WHOLE trace, not just the auth spans: a leak anywhere is
    # a leak, and a demo trace gets screenshotted.
    blob = json.dumps(
        [
            {"n": k.name, "i": k.inputs, "o": k.outputs, "e": k.extra}
            for k in kids
        ],
        default=str,
    )
    secrets = {
        "the corpus credential": os.environ.get("MDA_DEV_CONTEXT_HUB_CORPUS", ""),
        "the caller's API key": KEY,
    }
    for label, value in secrets.items():
        if not value:
            continue
        leaked = value in blob
        bad += leaked
        print(f"  [{'FAIL' if leaked else 'PASS'}] {label} is NOT in the trace")
    import re

    shaped = set(re.findall(r"lsv2_(?:pt|sk)_[0-9a-f]{8}", blob))
    bad += bool(shaped)
    print(f"  [{'FAIL' if shaped else 'PASS'}] no key-shaped string anywhere in {len(kids)} spans")

    print(f"\n{'FAILED' if bad else 'all auth-visibility checks passed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
