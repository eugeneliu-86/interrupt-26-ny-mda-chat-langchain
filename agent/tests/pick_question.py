"""Choosing the demo question from real runs (ph. 05 §4).

    uv run python -m tests.pick_question

Runs every candidate three times per role against the deployment and reports
the four criteria a machine can judge, plus the answers themselves for the two
a machine cannot.

WHY THREE RUNS. A question that answers differently run to run is a bad demo
question no matter how good it looks once, and the failure appears on stage
rather than in rehearsal. Three runs per role is the cheapest number that can
distinguish "stable" from "got lucky".

WHY THIS EXISTS SEPARATELY FROM THE OFFLINE SCORER. `score_candidates.py`
measures whether a page *looks* relevant; this measures whether the agent
*answers*. Phase 05 has one documented case where those disagreed
("How do I deploy a managed deep agent?" — scored beat 1, double-refused
live), and it is kept in the candidate list below as a regression marker.

Criteria 2 (both answers correct) and 5 (legible in fifteen seconds) are
deliberately NOT automated. They are judgment calls about what an audience
will accept, and a script that pretended to score them would launder taste as
measurement. The answers are printed in full so a person can make the call.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib

from tests.deployment import ask

RUNS = 3

#: (label, question). Order is the order they are reported in.
CANDIDATES = [
    ("A", "Do we require retry middleware on model calls?"),
    ("B", "How should agent code be structured and reviewed?"),
    ("C", "What environments do we have?"),
    ("D", "What timeout should I use for a model call?"),
    ("E", "How do I deploy a managed deep agent?"),  # known dead; kept as a marker
]

#: Beat 2 is a different shape and gets its own check: the engineer answers
#: from the runbooks and the employee cannot reach them at all.
BEAT_TWO = "What is our on-call escalation path?"


def judge(runs: dict[str, list[dict]]) -> dict:
    eng, emp = runs["engineer"], runs["employee"]

    answered = all(r["prefixes"] and not r["rejected"] for r in eng + emp)
    differ = all(e["text"] != m["text"] for e, m in zip(eng, emp))
    pages_differ = all(e["pages"] != m["pages"] for e, m in zip(eng, emp))
    prefers = sum("engineeringDocs" in r["prefixes"] for r in eng)
    stable = (
        len({frozenset(r["prefixes"]) for r in eng}) == 1
        and len({frozenset(r["prefixes"]) for r in emp}) == 1
    )
    return {
        "c1_both_answer": answered,
        "c3_answers_differ": differ,
        "c3_pages_differ": pages_differ,
        "c4_engineer_prefers_runbooks": f"{prefers}/{RUNS}",
        "c4_pass": prefers == RUNS,
        "stable_across_runs": stable,
        "verdict": (
            "BEAT 1" if answered and differ and prefers == RUNS and stable
            else "beat 2" if answered and all("engineeringDocs" not in r["prefixes"] for r in emp) and prefers == RUNS and not all(m["prefixes"] for m in emp)
            else "reject"
        ),
    }


def main() -> int:
    work: dict[tuple[str, str, int], cf.Future] = {}
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        for label, q in CANDIDATES:
            for role in ("engineer", "employee"):
                for i in range(RUNS):
                    work[(label, role, i)] = pool.submit(ask, q, role)
        for role in ("engineer", "employee"):
            work[("BEAT2", role, 0)] = pool.submit(ask, BEAT_TWO, role)
        done = {k: f.result() for k, f in work.items()}

    report: dict = {"runs": RUNS, "candidates": {}}
    for label, q in CANDIDATES:
        runs = {
            role: [done[(label, role, i)] for i in range(RUNS)]
            for role in ("engineer", "employee")
        }
        j = judge(runs)
        report["candidates"][label] = {
            "question": q,
            **j,
            "engineer": [
                {"prefixes": sorted(r["prefixes"]), "pages": sorted(r["pages"]),
                 "trace": r["trace"], "text": r["text"]}
                for r in runs["engineer"]
            ],
            "employee": [
                {"prefixes": sorted(r["prefixes"]), "pages": sorted(r["pages"]),
                 "trace": r["trace"], "text": r["text"]}
                for r in runs["employee"]
            ],
        }
        print(f"\n{'=' * 78}\n[{label}] {j['verdict']:6}  {q}")
        print(f"  c1 both answer      {j['c1_both_answer']}")
        print(f"  c3 answers differ   {j['c3_answers_differ']}  (pages differ: {j['c3_pages_differ']})")
        print(f"  c4 eng prefers eng  {j['c4_engineer_prefers_runbooks']}")
        print(f"  stable across runs  {j['stable_across_runs']}")
        for role in ("engineer", "employee"):
            for i, r in enumerate(runs[role]):
                print(f"    {role:8} #{i + 1}  {sorted(r['prefixes'])} {sorted(r['pages'])}")
        print(f"\n  --- engineer run 1 ---\n{runs['engineer'][0]['text'][:700]}")
        print(f"\n  --- employee run 1 ---\n{runs['employee'][0]['text'][:700]}")
        print(f"\n  traces: eng {runs['engineer'][0]['trace']}")
        print(f"          emp {runs['employee'][0]['trace']}")

    eng2, emp2 = done[("BEAT2", "engineer", 0)], done[("BEAT2", "employee", 0)]
    beat2_ok = (
        "engineeringDocs" in eng2["prefixes"]
        and "engineeringDocs" not in emp2["prefixes"]
        and bool(emp2["text"])
    )
    report["beat_two"] = {
        "question": BEAT_TWO, "pass": beat2_ok,
        "engineer": {"prefixes": sorted(eng2["prefixes"]), "pages": sorted(eng2["pages"]),
                     "trace": eng2["trace"], "text": eng2["text"]},
        "employee": {"prefixes": sorted(emp2["prefixes"]), "trace": emp2["trace"],
                     "text": emp2["text"]},
    }
    print(f"\n{'=' * 78}\n[BEAT 2] {'PASS' if beat2_ok else 'FAIL'}  {BEAT_TWO}")
    print(f"  engineer {sorted(eng2['prefixes'])} {sorted(eng2['pages'])}\n{eng2['text'][:500]}")
    print(f"\n  employee {sorted(emp2['prefixes'])}\n{emp2['text'][:500]}")
    print(f"\n  traces: eng {eng2['trace']}\n          emp {emp2['trace']}")

    out = pathlib.Path(__file__).parent / "question_selection.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n-> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
