"""The role gate, tested offline against real LangChain request objects.

No network, no credential, no LLM. The gate is a pure function of a role and a
tool list, so it can be asserted exhaustively — including the things a live run
cannot show: that a handler was never called, that a surface is exactly a
subset, that nothing reached the network.

EXPECTED SURFACES ARE COMPUTED FROM `contracts.grants`, never written as
literals. A test that hardcodes `{"productDocs__search_docs", …}` keeps passing
after someone widens a grant — which is precisely the change that must fail.
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain.messages import SystemMessage, ToolMessage

from context_schema import RequestContext
from contracts.grants import CORPORA, CORPUS_BLURB, GRANTS, primary_order
from contracts.roles import ROLES
from middleware import role_gate as gate_mod
from middleware.role_gate import (
    deny_ungranted_tool,
    granted_access_section,
    reject_unknown_role,
    role_gate,
)


class StubModel:
    """ModelRequest requires a model; nothing under test calls it."""


BUILTINS = ["write_todos", "ls", "read_file", "task"]
DOCS_TOOLS = [f"{p}__{verb}" for p in CORPORA for verb in ("search_docs", "fetch_doc")]


def fake_tool(name: str):
    return SimpleNamespace(name=name)


def runtime_for(role: str | None):
    ctx = None if role is None else RequestContext(
        role=role, display_name=f"probe-{role}"
    )
    return SimpleNamespace(context=ctx)


def make_request(role: str | None, tools: list[str] | None = None) -> ModelRequest:
    return ModelRequest(
        model=StubModel(),
        messages=[],
        system_message=SystemMessage(content="BASE INSTRUCTIONS"),
        tools=[fake_tool(n) for n in (tools if tools is not None else DOCS_TOOLS + BUILTINS)],
        runtime=runtime_for(role),
    )


def gated(role: str, tools: list[str] | None = None) -> ModelRequest:
    """Run role_gate and return the request the model would have received."""
    seen: list[ModelRequest] = []

    async def handler(request):
        seen.append(request)
        return "answer"

    asyncio.run(gate_mod.role_gate.awrap_model_call(make_request(role, tools), handler))
    assert seen, "role_gate did not call the handler"
    return seen[0]


def surface(role: str, tools: list[str] | None = None) -> set[str]:
    return {t.name for t in gated(role, tools).tools}


# --- layer 1: the tool surface ------------------------------------------------


@pytest.mark.parametrize("role", sorted(ROLES))
def test_surface_is_exactly_the_granted_docs_tools_plus_builtins(role):
    expected = {
        f"{p}__{verb}" for p in GRANTS[role] for verb in ("search_docs", "fetch_doc")
    } | set(BUILTINS)
    assert surface(role) == expected


def test_employee_surface_is_a_strict_subset_of_engineer():
    """This is what 'nested' means, and the strictness is what guarantees beat
    2 exists at all. If these were ever equal the demo would still 'work' while
    demonstrating nothing."""
    assert surface("employee") < surface("engineer")


def test_employee_cannot_see_any_engineering_tool():
    assert not {n for n in surface("employee") if n.startswith("engineeringDocs")}


@pytest.mark.parametrize("role", sorted(ROLES))
def test_harness_builtins_survive_the_gate(role):
    """A naive prefix filter drops them and breaks the agent in a way that
    looks like a model problem."""
    assert set(BUILTINS) <= surface(role)


def test_a_tool_with_an_unknown_prefix_is_dropped():
    """Neither granted nor a built-in: the gate must not pass it through."""
    got = surface("engineer", DOCS_TOOLS + BUILTINS + ["secretDocs__search_docs"])
    assert "secretDocs__search_docs" not in got


# --- layer 1: the prompt section ---------------------------------------------


@pytest.mark.parametrize("role", sorted(ROLES))
def test_prompt_names_exactly_the_granted_corpora_in_preference_order(role):
    section = granted_access_section(primary_order(role))
    named = [c for c in CORPORA if CORPUS_BLURB[c] in section]
    assert set(named) == GRANTS[role]
    positions = [section.index(CORPUS_BLURB[c]) for c in primary_order(role)]
    assert positions == sorted(positions), "corpora are not in preference order"


@pytest.mark.parametrize("role", sorted(ROLES))
def test_prompt_and_tool_surface_agree(role):
    """The invariant the single-hook design exists to guarantee: the prompt
    cannot claim access the tool list does not have."""
    req = gated(role)
    in_prompt = {c for c in CORPORA if CORPUS_BLURB[c] in req.system_message.content}
    in_tools = {t.name.split("__", 1)[0] for t in req.tools if "__" in t.name}
    assert in_prompt == in_tools


def test_base_instructions_are_appended_to_not_replaced():
    """Replacing drops instructions.md, which Context Hub is supposed to own."""
    content = gated("engineer").system_message.content
    assert content.startswith("BASE INSTRUCTIONS")
    assert "## Granted access" in content


def test_the_two_roles_get_different_prompt_sections():
    a = gated("engineer").system_message.content
    b = gated("employee").system_message.content
    assert a != b


# --- layer 0: reject an undeclared or unknown role ---------------------------


@pytest.mark.parametrize("role", [None, "admin", "", "ENGINEER"])
def test_an_invalid_role_fails_before_any_model_call(role):
    with pytest.raises(ValueError) as err:
        asyncio.run(reject_unknown_role.abefore_agent({}, runtime_for(role)))
    assert "engineer" in str(err.value) and "employee" in str(err.value)


@pytest.mark.parametrize("role", sorted(ROLES))
def test_a_valid_role_passes_layer_0(role):
    assert asyncio.run(reject_unknown_role.abefore_agent({}, runtime_for(role))) is None


# --- layer 2: deny an ungranted call ----------------------------------------


def tool_call_request(role: str, name: str):
    return SimpleNamespace(
        tool_call={"name": name, "id": "call-1", "args": {}},
        runtime=runtime_for(role),
    )


def test_an_ungranted_call_is_denied_and_the_handler_never_runs():
    called: list[str] = []

    async def handler(request):
        called.append(request.tool_call["name"])
        return "should not happen"

    gate_mod.denials.clear()
    out = asyncio.run(deny_ungranted_tool.awrap_tool_call(
        tool_call_request("employee", "engineeringDocs__fetch_doc"), handler))
    assert isinstance(out, ToolMessage)
    assert out.status == "error"
    assert "Access denied" in out.content
    assert not called, "the tool ran despite being denied"
    assert gate_mod.denials == ["engineeringDocs__fetch_doc"]


@pytest.mark.parametrize("name", ["productDocs__search_docs", "write_todos"])
def test_a_granted_or_builtin_call_reaches_the_handler(name):
    called: list[str] = []

    async def handler(request):
        called.append(request.tool_call["name"])
        return "ran"

    gate_mod.denials.clear()
    out = asyncio.run(deny_ungranted_tool.awrap_tool_call(
        tool_call_request("employee", name), handler))
    assert out == "ran"
    assert called == [name]
    assert gate_mod.denials == []


# --- the hooks themselves ----------------------------------------------------


@pytest.mark.parametrize("mw", [reject_unknown_role, role_gate, deny_ungranted_tool])
def test_every_hook_is_async(mw):
    """MDA always invokes with ainvoke/astream, so a sync-only hook never runs —
    and never running is silent."""
    overridden = [
        h for h in ("abefore_agent", "awrap_model_call", "awrap_tool_call",
                    "before_agent", "wrap_model_call", "wrap_tool_call")
        if getattr(type(mw), h, None) is not getattr(AgentMiddleware, h, None)
    ]
    assert overridden, f"{mw} overrides no hook at all"
    for h in overridden:
        assert h.startswith("a"), f"{mw} overrides the sync hook {h}"
        assert inspect.iscoroutinefunction(getattr(mw, h))


def test_the_context_cannot_collide_with_build_metadata():
    """MDA mirrors every context field into root-run metadata, so a context
    field named like a build metadata key overwrites it. `demo_version` was
    such a field and was removed."""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(RequestContext)}
    assert "demo_version" not in fields
    assert fields == {"role", "display_name"}


# --- the built-in heuristic --------------------------------------------------

#: Every tool name the compiled Deep Agents harness defines, observed in
#: `.mda/build/.venv/**/deepagents`. Written as literals deliberately: this is
#: the OBSERVED environment, and a change to it should fail loudly.
HARNESS_TOOLS = [
    "cancel_async_task", "check_async_task", "compact_conversation", "delete",
    "edit_file", "execute", "glob", "grep", "list_async_tasks", "ls",
    "read_file", "rubric_grader", "start_async_task", "task",
    "update_async_task", "write_file",
]


@pytest.mark.parametrize("name", HARNESS_TOOLS)
def test_no_harness_tool_is_mistaken_for_a_gated_one(name):
    assert gate_mod._is_builtin(name), f"{name} would be filtered by the gate"


@pytest.mark.parametrize("role", sorted(ROLES))
def test_all_harness_tools_survive_the_gate(role):
    got = surface(role, DOCS_TOOLS + HARNESS_TOOLS)
    assert set(HARNESS_TOOLS) <= got


def test_a_name_starting_with_the_separator_is_a_builtin():
    """The harness ships strings like `__deepagents_subagent_response_format`.
    An empty prefix must not make a tool invisible to every role."""
    assert gate_mod._prefix_of("__deepagents_thing") is None
    assert gate_mod._is_builtin("__deepagents_thing")
    assert "__deepagents_thing" in surface("employee", DOCS_TOOLS + ["__deepagents_thing"])


# --- the middleware ORDER is load-bearing (ph. 03 §7) -----------------------


def test_reordering_the_middleware_list_breaks_this():
    """The chain's order is a contract, so it gets an assertion.

    `reject_unknown_role` must run first: every hook after it assumes the
    role is one of two values, and `role_gate` would raise a bare KeyError
    on an unknown one instead of the message C1 promises. `role_gate` must
    precede `deny_ungranted_tool`, because layer 2 only ever sees calls
    layer 1 failed to remove.

    An order that does not matter should not be specified; one that does
    should be protected. This is the protection.
    """
    import ast
    import pathlib

    src = pathlib.Path(__file__).resolve().parent.parent / "agent.py"
    tree = ast.parse(src.read_text())

    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "middleware" and isinstance(kw.value, ast.List):
                names = [e.id for e in kw.value.elts if isinstance(e, ast.Name)]

    assert names == [
        "reject_unknown_role",
        "role_gate",
        "deny_ungranted_tool",
    ], f"middleware order changed: {names}"
