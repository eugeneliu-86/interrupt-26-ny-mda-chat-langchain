from managed_deepagents import define_deep_agent
from context_schema import RequestContext
from contracts.version import DEMO_VERSION
from middleware.role_gate import deny_ungranted_tool, reject_unknown_role, role_gate
from tools.corpus import TOOLS

agent = define_deep_agent(
    name="role-aware-docs-assistant",
    model="langsmith:openai/gpt-5.6-luna",
    context_schema=RequestContext,
    metadata={"demo": "role-aware-docs", "demo_version": DEMO_VERSION},
    tools=TOOLS,
    middleware=[reject_unknown_role, role_gate, deny_ungranted_tool],
)
