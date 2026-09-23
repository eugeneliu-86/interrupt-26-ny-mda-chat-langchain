"""The agent's demo version, stamped onto every run's trace metadata (C9).

    ┌──────────────────────────────────────────────────────────────┐
    │  BUMP THIS when you change how the agent answers.            │
    │  v1 -> v2 -> v3 …  no dots, no dates, no git SHA.            │
    └──────────────────────────────────────────────────────────────┘

WHY A HAND-MAINTAINED NUMBER. A derived version (a git SHA, a source hash)
changes on every commit, including ones that cannot affect an answer — a test,
a comment, a doc. Trace history then fragments into versions that are not
meaningfully different, and "compare v1 against v2" stops being a question with
an answer. A number someone bumps deliberately marks the changes worth
comparing, and `git log contracts/version.py` recovers the commit behind each.

WHAT COUNTS AS A BUMP. Anything that could change what a run does or produces:
the grants, the corpora, a tool's behaviour, the instructions or the skill, the
model, the middleware chain. Not tests, not comments, not the eval harness.

WHERE IT LANDS. `agent.py` passes it to `define_deep_agent(metadata=...)`,
which MDA applies to the ROOT LangSmith run — so no caller can set or override
it, and it describes which BUILD answered rather than what was asked. The
per-run half of the trace contract (role, granted) comes from middleware.

It is compiled in, so a bump only takes effect on the next deploy.
"""

from __future__ import annotations

#: The current demo version. See the bump rule above.
DEMO_VERSION = "v8"

#: What changed in each version, newest first. One line each.
HISTORY = {
    "v8": "Layer 1's decision became its own `authorize_tool_surface` span. As "
          "metadata it did not attach to the hook's span at all — it was "
          "inherited by the middleware spans underneath, appearing four times on "
          "spans that made no decision.",
    "v7": "Auth made visible in the trace. `resolve_connection` is now an explicit "
          "span around the Agent Auth fetch (credential never recorded), and all "
          "three gate layers write their decision — role, granted, withheld, "
          "removed tools — onto their own spans instead of reporting nothing.",
    "v6": "Renamed the two simulated identities to Lang (engineer) and Polly "
          "(employee). Display only — no grant, tool or answer changes — but the "
          "label reaches every run as `display_name`, so the traces change and "
          "the build that produced them should say so.",
    "v5": "Corpus provenance: each corpus tool stamps the Context Hub commit it "
          "read onto its own trace span, so a run says which document version "
          "answered it. Metadata only — the model never sees the hash.",
    "v4": "Trace contract corrected: dropped the metadata middleware (MDA mirrors "
          "context into root metadata by itself) and removed demo_version from the "
          "context, which was overwriting the build's own value.",
    "v3": "Role gating: typed run context, three-layer middleware, per-run trace "
          "metadata. The employee surface is now a strict subset of the engineer's.",
    "v2": "Corpus tools added: productDocs and engineeringDocs search/fetch over "
          "two private Context Hub repos. No gating yet — every caller reaches both.",
    "v1": "Bootstrap: instructions, one skill, no tools.",
}
