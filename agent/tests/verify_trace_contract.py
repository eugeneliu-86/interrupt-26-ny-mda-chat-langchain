"""The trace contract, checked against LangSmith (ph. 05 §3, C9).

    uv run python -m tests.verify_trace_contract [run_id …]

With no arguments it reads the run ids `verify_deployment.py` recorded.

THE CLAIM UNDER TEST: *"LangSmith traces show which tools and connections were
available and invoked for each role."* §3 verifies it the way the audience
will — by handing someone one trace URL and asking four questions:

    1. Which identity made this run?
    2. Which documentation corpora could it reach?
    3. Which did it actually call?
    4. Was anything denied?

A person answers those by reading the UI. This script answers them from the
API, which proves the DATA IS THERE. It cannot prove the data is *findable* in
about a minute by someone who has not seen the repo — that is a human check,
and §3's acceptance criterion says so.

WHAT IS DELIBERATELY NOT HERE. There is no `granted` metadata key. One was
attempted and removed in v4: a middleware run-tree write does not reach the
root run, so the value never appeared. Question 2 is answered from the model
call's tool list instead, which is better evidence anyway — it is what the
model was actually handed, not what we claim we handed it.
"""

from __future__ import annotations

import json
import pathlib
import sys

from langsmith import Client

from contracts.grants import GRANTS, granted_prefixes
from tests.deployment import KEY, trace_url


def descendants(client: Client, trace_id: str) -> list:
    return list(client.list_runs(trace_id=trace_id, is_root=False, limit=100))


def check(client: Client, run_id: str) -> dict:
    root = client.read_run(run_id)
    meta = (root.extra or {}).get("metadata", {})
    kids = descendants(client, root.trace_id)

    # A REJECTED RUN IS A DIFFERENT SHAPE, and judging it by the four
    # questions would score a correct rejection as a broken trace. C1 stops
    # the run at `before_agent`, so there is no tool list and no model call —
    # and *that emptiness is the answer* a cold reader gets: "nobody valid
    # made this run, so it did not happen."
    #
    # Detected from the root error plus the absence of any model call, NOT
    # from a missing role: MDA mirrors the context it was given, so a run
    # rejected for `role="admin"` still carries `metadata.role = "admin"`.
    # A DE filtering the project on `metadata.role` therefore sees THREE
    # values, not two — the third being whatever an invalid caller sent. That
    # is correct behaviour and is recorded in docs/DE-onboarding.md, because
    # it looks like a leak until you know the run died before the model.
    rejected = root.error is not None

    # Q1 — identity. Mirrored from the run context by MDA; we write nothing.
    role = meta.get("role")
    q1 = rejected or (role in ("engineer", "employee") and bool(meta.get("display_name")))
    # A rejection must also be legibly empty: no model call, no tool call.

    # Q2 — the surface. The tool list on the first model call IS the answer:
    # it is what the model was handed after `role_gate` filtered it.
    llm = [r for r in kids if r.run_type == "llm"]
    offered: set[str] = set()
    for r in llm:
        for t in ((r.extra or {}).get("invocation_params", {}) or {}).get("tools", []) or []:
            name = (
                t.get("name")
                or (t.get("function") or {}).get("name")
                or ""
            )
            if "__" in name:
                offered.add(name.split("__", 1)[0])
    q2 = rejected or (bool(offered) and offered == set(granted_prefixes(role)))

    # Q3 — what it actually called.
    called = {
        r.name.split("__", 1)[0]
        for r in kids
        if r.run_type == "tool" and "__" in (r.name or "")
    }
    q3 = rejected or bool(called)

    # Q4 — denials. Absent in a clean run, which is itself the answer.
    denied = [r for r in kids if r.run_type == "tool" and (r.error or "")]

    return {
        "run_id": str(run_id),
        "trace": trace_url(str(run_id)),
        "rejected": rejected,
        "q1_identity": {"pass": q1, "role": role,
                        "display_name": meta.get("display_name")},
        "q2_reachable": {"pass": q2, "offered": sorted(offered),
                         "granted": sorted(GRANTS.get(role, ())) if role else []},
        "q3_called": {"pass": q3, "called": sorted(called),
                      "tools": sorted({r.name for r in kids if r.run_type == "tool"})},
        "q4_denied": {"pass": True, "count": len(denied)},
        "demo_version": meta.get("demo_version"),
        # ONE MODEL, TWO SPELLINGS. The gateway span carries the routed name
        # (`openai/gpt-5.6-luna`) and the provider span the resolved one
        # (`gpt-5.6-luna`). Comparing them raw makes one model look like two,
        # which would falsely fail the "only the tools differ" claim.
        "model": sorted({
            (r.extra or {}).get("metadata", {}).get("ls_model_name", "?").rsplit("/", 1)[-1]
            for r in llm
        }),
    }


def main() -> int:
    ids = sys.argv[1:]
    if not ids:
        rows = json.loads((pathlib.Path(__file__).parent / "verification.json").read_text())
        ids = [r["run_id"] for r in rows if r["run_id"]]
    client = Client(api_key=KEY)

    results, bad = [], 0
    for rid in ids:
        try:
            res = check(client, rid)
        except Exception as exc:  # a trace not yet queryable is a real outcome
            print(f"[SKIP] {rid}: {type(exc).__name__}: {exc}")
            continue
        results.append(res)
        ok = all(res[k]["pass"] for k in ("q1_identity", "q2_reachable", "q3_called", "q4_denied"))
        bad += not ok
        tag = "REJECTED-OK" if res["rejected"] else ("PASS" if ok else "FAIL")
        print(
            f"[{tag}] {rid}\n"
            f"        Q1 identity   {res['q1_identity']['role']} / "
            f"{res['q1_identity']['display_name']}\n"
            f"        Q2 reachable  {res['q2_reachable']['offered']} "
            f"(granted {res['q2_reachable']['granted']})\n"
            f"        Q3 called     {res['q3_called']['called']}  "
            f"{res['q3_called']['tools']}\n"
            f"        Q4 denied     {res['q4_denied']['count']}\n"
            f"        version {res['demo_version']}  model {res['model']}"
        )

    versions = {r["demo_version"] for r in results}
    roles = {r["q1_identity"]["role"] for r in results if not r["rejected"]}
    models = {m for r in results for m in r["model"]}
    print(f"\ndemo_version across {len(results)} runs: {versions}")
    print(f"roles present (project filters cleanly on metadata.role): {roles}")
    print(f"model across both roles: {models}")

    if len(versions) != 1:
        print("FAIL: demo_version is not uniform across runs")
        bad += 1
    if len(models) > 1:
        print("FAIL: the two roles did not resolve to one model")
        bad += 1

    out = pathlib.Path(__file__).parent / "trace_contract.json"
    out.write_text(json.dumps(results, indent=2, default=str) + "\n")
    print(f"-> {out.name}  ({len(results) - bad} clean)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
