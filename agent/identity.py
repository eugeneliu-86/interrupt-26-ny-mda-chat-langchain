"""Who may call this deployment (C10).

Callers present a LangSmith workspace API key as `x-api-key`. This answers
whether a caller is ALLOWED; it does not give each person private threads.
Every DE holding a key for this workspace resolves to one identity, and they
will see each other's threads. That is acceptable for a shared demo and is
written here, next to the code that causes it, so nobody discovers it on stage.

A workspace API key is workspace-scoped, not request-scoped, so it must never
reach a browser: the UI keeps it in its server runtime (C5, ph. 06 §1).

This is also NOT where the demo's roles come from. The role arrives as typed
run context set by the UI's server route (C3), and is enforced by middleware.
Identity here answers "may you call this deployment at all".

Upgrade path, out of scope for this build: auth.supabase(project_ref=...)
gives each signed-in person private threads and lets a browser call the
deployment directly with a Bearer token. Adding it later does not backfill
owner metadata onto existing threads, so it is a migration, not a config
change.
"""

from managed_deepagents import auth, define_identity

identity = define_identity(auth=auth.langsmith_api_key())
