# Dependency standards

The agent libraries iterate quickly. These rules exist because we have been
broken by silent minor-version changes more than once.

## Rules

- **Pin minimum versions** of `langchain`, `langgraph` and `langsmith` in
  `pyproject.toml`. An unpinned dependency means a rebuild can change agent
  behaviour with no code change and no version bump.
- **Pin the exact version of the agent runtime SDK.** Not a minimum — exact.
  The runtime decides how the agent is compiled, and a floating runtime makes
  two builds of the same commit different artifacts.
- **`agent-checks` fails on an unpinned agent dependency.** If the check is
  wrong, fix the check; do not add an exemption.
- **Upgrades are their own `PLAT-` ticket**, never bundled with a behaviour
  change. When a deploy breaks and the diff contains both an upgrade and a
  prompt change, you cannot tell which broke it.
- **An upgrade bumps the agent's version counter**, because it can change
  behaviour even with an identical prompt.
