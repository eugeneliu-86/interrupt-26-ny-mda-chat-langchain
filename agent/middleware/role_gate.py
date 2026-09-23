"""Role gating: three layers, in the order they run (C1, C6, C8).

    reject_unknown_role   before_agent     no valid role -> the run fails
    role_gate             wrap_model_call  the model sees only granted tools
    deny_ungranted_tool   wrap_tool_call   an ungranted call is refused

Layer 2 exists for what layer 1 cannot promise. Layer 1 filters what the model
SEES, which a sceptical reader will correctly say is not enforcement. Layer 2 is
enforcement, and it returns a readable `ToolMessage` rather than raising, so a
leak becomes a visible denial the model can recover from instead of a dead run.

All hooks are ASYNC. Managed Deep Agents always invokes with `ainvoke`/`astream`,
so a sync-only hook never runs — and never running is a silent failure, which is
the worst kind.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import before_agent, wrap_model_call, wrap_tool_call
from langchain.messages import SystemMessage, ToolMessage

from contracts.grants import CORPUS_BLURB, granted_prefixes, primary_order

#: MDA/Deep Agents harness tools (todo list, filesystem, task) carry no
#: `{corpus}__` prefix. A naive prefix filter removes them and quietly breaks
#: the agent, so anything without the separator is treated as a built-in.
_SEP = "__"


def _prefix_of(tool_or_name: Any) -> str | None:
    """The `{corpus}` part of a `{corpus}__{verb}` name, or None for a built-in.

    An EMPTY prefix counts as no prefix. The compiled harness contains strings
    such as `__deepagents_subagent_response_format`; a name beginning with the
    separator would otherwise yield `""`, which is not None, and the tool would
    be silently dropped for every role. None of the harness's actual tool names
    contain the separator today — verified against the compiled build — but a
    filter that fails closed on an unfamiliar name is the wrong default when the
    failure looks like the model misbehaving.
    """
    name = getattr(tool_or_name, "name", None) or (
        tool_or_name if isinstance(tool_or_name, str) else ""
    )
    if isinstance(tool_or_name, dict):                 # provider-format tool dict
        name = tool_or_name.get("name", "")
    if _SEP not in name:
        return None
    prefix = name.split(_SEP, 1)[0]
    return prefix or None


def _is_builtin(tool_or_name: Any) -> bool:
    return _prefix_of(tool_or_name) is None


# --- layer 0: no valid role, no run ------------------------------------------


@before_agent
async def reject_unknown_role(state: Any, runtime: Any) -> None:
    """Fail the run before any model call if the role is missing or unknown (C1).

    Deliberately does NOT downgrade to a least-privilege surface. A silent
    downgrade is the wrong lesson to teach from a stage: if a caller does not
    declare a role, the honest behaviour is to refuse, visibly. The UI always
    sets a role, so this only fires for a raw client — which is exactly when it
    should.
    """
    ctx = getattr(runtime, "context", None)
    role = getattr(ctx, "role", None) if ctx is not None else None
    if not role:
        raise ValueError(
            "this deployment requires context.role; expected engineer or employee"
        )
    granted_prefixes(role)  # raises ValueError on an unknown role


# --- layer 1: the tool surface and the prompt, from one computed set ---------


def granted_access_section(order: tuple[str, ...]) -> str:
    """The per-run prompt section, ordered most authoritative first (C2).

    Ordering is PREFERENCE, not enforcement: with nested grants an engineer can
    read the shared corpus too. What is enforced is the tool list below.
    """
    lines = "\n".join(
        f"{i}. {CORPUS_BLURB[p]}" for i, p in enumerate(order, start=1)
    )
    return (
        "## Granted access\n\n"
        "You may search only these documentation corpora in this run, listed "
        "most authoritative for your caller first:\n\n"
        f"{lines}\n\n"
        "Prefer the highest-listed corpus that covers the question, and say "
        "which one you used. Fall back to a lower one only when the higher "
        "corpus does not cover it.\n\n"
        "You have no tools for anything else. Refuse questions that need other "
        "documentation, and name what you do have."
    )


@wrap_model_call
async def role_gate(request: Any, handler: Any) -> Any:
    """Expose only the granted tools, and describe exactly those (C6, C8).

    ONE hook does both on purpose. Split across two, they can disagree — the
    prompt claiming a corpus the tool list has dropped, or the reverse — and the
    agent then refuses something it can do or promises something it cannot.
    Computing the grant once makes that class of bug unrepresentable.
    """
    role = request.runtime.context.role
    prefixes = granted_prefixes(role)
    order = primary_order(role)          # same set, ordered (asserted in contracts)

    tools = [t for t in request.tools if _is_builtin(t) or _prefix_of(t) in prefixes]

    base = request.system_message.content if request.system_message else ""
    section = granted_access_section(order)
    return await handler(
        request.override(
            tools=tools,
            # APPEND. Replacing drops instructions.md, which is the one thing
            # Context Hub is supposed to own (C8).
            system_message=SystemMessage(content=f"{base}\n\n{section}"),
        )
    )


# --- layer 2: deny an ungranted call, visibly --------------------------------

#: Incremented whenever layer 2 fires. Should be zero across a demo run: if it
#: is not, layer 1 leaked and the trace will show where.
denials: list[str] = []


@wrap_tool_call
async def deny_ungranted_tool(request: Any, handler: Any) -> Any:
    """Refuse a call to a tool this role was never granted (C6).

    Returns a ToolMessage rather than raising, so the model reads the denial and
    produces a proper refusal instead of the run dying — the difference between
    a graceful demo and a red trace.
    """
    name = request.tool_call["name"]
    prefix = _prefix_of(name)
    if prefix is None:
        return await handler(request)          # harness built-in

    role = request.runtime.context.role
    if prefix not in granted_prefixes(role):
        denials.append(name)
        return ToolMessage(
            content=(
                f"Access denied: {name} is not available to this caller. "
                "Refuse the request and name the documentation you do have."
            ),
            tool_call_id=request.tool_call["id"],
            status="error",
        )
    return await handler(request)
