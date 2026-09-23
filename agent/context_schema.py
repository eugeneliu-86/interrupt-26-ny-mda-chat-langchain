"""Per-run context, set by the caller's server (C3, C5).

WHY CONTEXT AND NOT A MESSAGE. The role must arrive on a channel the model
cannot write to. A role appended to the user message, inferred from the API key,
or stored on the thread is a role the model — or a prompt injection — can
influence. `context` is the only channel that is set by the caller and never
authored by the agent.

This is a DECLARATION of shape, not a trust boundary. Nothing here is
authenticated: the role is whatever the caller sent. The trust boundary is the
UI's server route, which sets it from a server-side session and overwrites
whatever the browser asked for (ph. 06 §1).

`define_deep_agent(context_schema=RequestContext)` is accepted by the wheel
even though the published parameter table omits it — verified against
mda 0.7.4.

NO `demo_version` FIELD, deliberately. **MDA mirrors every context field into
the root run's metadata**, so a context field named `demo_version` silently
overwrote the build's own static `demo_version` — exactly the value C9 says no
caller may set. Measured: a probe sending `demo_version="e2e"` replaced `v3` on
the root run. The build owns that key; the caller must not have a field that
can collide with it.

That mirroring is also why there is no metadata middleware: `role` and
`display_name` reach the trace on their own.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.roles import Role


@dataclass
class RequestContext:
    """What one run knows about its caller. Carries no content, no credentials.

    A dataclass rather than a dict buys attribute access and a coercion error
    at the edge if the caller sends the wrong shape — a better failure than a
    KeyError three hooks later. It does NOT validate the role's value:
    `Role` is a `Literal`, and dataclasses do not enforce those at runtime.
    `reject_unknown_role` does that.
    """

    # EVERY FIELD IS OPTIONAL, deliberately.
    #
    # LangGraph coerces the caller's dict into this dataclass BEFORE any
    # middleware runs, so a required field turns a malformed context into
    # `TypeError: __init__() missing 3 required positional arguments` — a Python
    # internals leak instead of "expected engineer or employee". With defaults,
    # coercion always succeeds and `reject_unknown_role` produces the message
    # that actually helps. The run still fails closed; only the wording improves.
    role: Role | None = None
    display_name: str = ""
