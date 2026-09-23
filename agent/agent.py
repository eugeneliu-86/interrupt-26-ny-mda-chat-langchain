"""The role-aware documentation agent.

One deployment. The role arrives as typed run context (C3) and middleware
deterministically decides which corpus tools the model may see (C6). Nothing
about the role is in the prompt the agent could edit, in the API key, or on the
thread.

WHAT IS DELIBERATELY ABSENT. `backend`, `store`, `checkpointer`, `memory`,
`skills`, `system_prompt` — the managed runtime owns those, and
`instructions.md` plus `skills/` are discovered from the filesystem rather than
passed here. Setting them would shadow Context Hub and break the live-injection
property phase 01 proved.

THE NAME IS FINAL. MDA uses it as the LangGraph assistant id and the default
deployment name, and the `context-hub-corpus` connection belongs to THIS
deployment. Renaming means recreating the connection.
"""

from managed_deepagents import define_deep_agent

from context_schema import RequestContext
from contracts.version import DEMO_VERSION
from middleware.role_gate import deny_ungranted_tool, reject_unknown_role, role_gate
from tools.corpus import TOOLS

agent = define_deep_agent(
    name="role-aware-docs-assistant",
    # Gateway route: colon after `langsmith`, SLASH before the model. A direct
    # provider call would be `openai:gpt-5.6-luna`, with a colon. Mixing the two
    # gives a provider-resolution error that reads like a missing key.
    model="langsmith:openai/gpt-5.6-luna",
    # Accepted by the wheel although the published parameter table omits it.
    context_schema=RequestContext,
    # The STATIC half of the trace contract (C9), applied to the root LangSmith
    # run. The per-run half (`role`, `display_name`) arrives by MDA mirroring
    # the context — see context_schema.py for why the context must not contain
    # a key that collides with these.
    metadata={"demo": "role-aware-docs", "demo_version": DEMO_VERSION},
    # Authored tools are not discovered. All four are present on every run;
    # middleware is the only thing that varies the surface per caller.
    tools=TOOLS,
    # ORDER MATTERS, and reading order should match execution order:
    #   reject_unknown_role  first — nothing else should run without a role, so
    #                        every hook after it may assume one of two values
    #   role_gate            filters the tool list and injects the prompt section
    #   deny_ungranted_tool  refuses a call layer 1 should already have removed
    #
    # There is NO metadata middleware. One was written and deleted: MDA mirrors
    # the run context into the root run's metadata by itself, so `role` and
    # `display_name` arrive without help, and a middleware run-tree write does
    # not reach the root run at all (measured — `granted` never appeared).
    middleware=[reject_unknown_role, role_gate, deny_ungranted_tool],
)
