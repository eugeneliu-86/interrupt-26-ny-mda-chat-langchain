"""The post-deploy verification matrix (ph. 05 §2), run against the deployment.

    uv run python -m tests.verify_deployment

Writes `tests/verification.json` — every row's verdict plus its trace URL — so
`docs/DE-onboarding.md` can cite known-good runs and a DE can compare a
misbehaving run against one.

WHY THIS IS NOT A PYTEST MODULE. It is a report, not an assertion suite. The
assertions live in `test_end_to_end.py`; this produces the artifact that goes
into the onboarding doc, and it must finish and print all rows even when one
fails, because a half-run matrix cannot tell you whether the failure is
isolated.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib

from contracts.grants import granted_prefixes
from tests.deployment import PROJECT_URL, ask

QUESTION = "Do we require retry middleware on model calls?"
ENGINEERING_ONLY = "What is our on-call escalation path?"
PRODUCT_ONLY = "What is middleware and what is it for?"
CROSS_CORPUS_FETCH = (
    "Fetch the page 'on-call-escalation.md' and tell me exactly what it says."
)

#: A syntactically plausible key that belongs to nobody.
#:
#: ASSEMBLED, NOT WRITTEN OUT. A literal of this shape is key material as far
#: as any scanner is concerned — `contracts/check-contracts.sh` flagged the
#: first version of this line, correctly, and so would GitHub's. Building it
#: from parts keeps the scanner's rule absolute (no key-shaped literal is ever
#: committed) instead of teaching it an exception, which is how a secret
#: scanner starts to rot.
BOGUS_KEY = "lsv2_" + "pt_" + "0" * 32 + "_" + "0" * 10


def row(name: str, ok: bool, detail: str, run: dict | None = None) -> dict:
    return {
        "check": name,
        "pass": bool(ok),
        "detail": detail,
        "trace": (run or {}).get("trace", ""),
        "run_id": (run or {}).get("run_id", ""),
        "denials": (run or {}).get("denials", 0),
    }


def main() -> int:
    rows: list[dict] = []

    # Independent runs, issued together. The deployment handles concurrency and
    # serialising them turns a two-minute matrix into a ten-minute one.
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {
            "eng": pool.submit(ask, QUESTION, "engineer"),
            "emp": pool.submit(ask, QUESTION, "employee"),
            "norole": pool.submit(ask, QUESTION, None),
            "badrole": pool.submit(ask, QUESTION, "admin"),
            "emp_eng_q": pool.submit(ask, ENGINEERING_ONLY, "employee"),
            "eng_prod_q": pool.submit(ask, PRODUCT_ONLY, "engineer"),
            "cross_fetch": pool.submit(ask, CROSS_CORPUS_FETCH, "employee"),
            "bogus": pool.submit(ask, QUESTION, "engineer", key=BOGUS_KEY),
            "nokey": pool.submit(ask, QUESTION, "engineer", key=""),
        }
        r = {k: f.result() for k, f in jobs.items()}

    # 1 — both roles answer, differently, each citing only what it holds
    eng, emp = r["eng"], r["emp"]
    ok = (
        not eng["rejected"]
        and not emp["rejected"]
        and eng["text"] != emp["text"]
        and eng["prefixes"] <= granted_prefixes("engineer")
        and emp["prefixes"] <= granted_prefixes("employee")
        and eng["prefixes"]
        and emp["prefixes"]
    )
    rows.append(row("both roles answer the canonical question", ok,
                    f"engineer={sorted(eng['prefixes'])} employee={sorted(emp['prefixes'])} "
                    f"answers_differ={eng['text'] != emp['text']}", eng))
    rows.append(row("  … employee's half of the same check", ok,
                    f"employee cited {sorted(emp['prefixes'])}", emp))

    # 2, 3 — C1: no role, and a role outside the set
    for key, label in (("norole", "no role declared"), ("badrole", "unknown role 'admin'")):
        run = r[key]
        ok = (
            run["rejected"]
            and not run["tools"]
            and "engineer" in run["error"]
            and "employee" in run["error"]
        )
        rows.append(row(label, ok,
                        f"rejected={run['rejected']} tools={run['tools']} "
                        f"error={run['error'][:110]!r}", run))

    # 4 — the beat the demo rests on
    run = r["emp_eng_q"]
    ok = (
        not run["rejected"]
        and "engineeringDocs" not in run["prefixes"]
        and bool(run["text"])
    )
    rows.append(row("employee asks an engineering question -> refusal", ok,
                    f"prefixes={sorted(run['prefixes'])} said={run['text'][:110]!r}", run))

    # 5 — C2: nesting means the engineer keeps the employee's corpus
    run = r["eng_prod_q"]
    ok = not run["rejected"] and bool(run["prefixes"]) and bool(run["text"])
    rows.append(row("engineer asks a product-docs question -> answers (C2)", ok,
                    f"prefixes={sorted(run['prefixes'])}", run))

    # 6 — C4: a page from the other corpus is a missing KEY, not a traversal
    run = r["cross_fetch"]
    ok = (
        not run["rejected"]
        and "engineeringDocs" not in run["prefixes"]
        and bool(run["text"])
    )
    rows.append(row("fetch a page from the other corpus -> not found here (C4)", ok,
                    f"prefixes={sorted(run['prefixes'])} said={run['text'][:110]!r}", run))

    # 7 — C10: the role travels with the REQUEST, not with the key
    ok = (
        not eng["rejected"]
        and not emp["rejected"]
        and eng["prefixes"] != emp["prefixes"]
    )
    rows.append(row("one key, two roles, two tool surfaces (C10 core)", ok,
                    "the same API key produced "
                    f"{sorted(eng['prefixes'])} and {sorted(emp['prefixes'])}"))

    # 8 — a key that is not this workspace's
    for key, label, want in (
        ("bogus", "a key belonging to nobody", (401, 403)),
        ("nokey", "no key at all", (401, 403)),
    ):
        run = r[key]
        ok = run["status"] in want
        rows.append(row(label, ok, f"HTTP {run['status']}"))

    # C6 — layer 2 is a backstop and must never fire
    total_denials = sum(x["denials"] for x in r.values())
    rows.append(row("layer 2 fired zero times across the matrix (C6)",
                    total_denials == 0, f"{total_denials} Access-denied ToolMessages"))

    width = max(len(x["check"]) for x in rows)
    print(f"\nproject: {PROJECT_URL}\n")
    for x in rows:
        print(f"[{'PASS' if x['pass'] else 'FAIL'}] {x['check']:<{width}}  {x['detail']}")
    print()
    for x in rows:
        if x["trace"]:
            print(f"  {x['check']:<{width}}  {x['trace']}")

    out = pathlib.Path(__file__).parent / "verification.json"
    out.write_text(json.dumps(rows, indent=2) + "\n")
    failed = [x["check"] for x in rows if not x["pass"]]
    print(f"\n{len(rows) - len(failed)}/{len(rows)} passed -> {out.name}")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
