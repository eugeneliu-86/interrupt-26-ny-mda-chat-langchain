# Middleware

> Hooks that wrap an agent's model and tool calls.

| | |
|---|---|
| Package | `langchain (langchain.agents.middleware)` |
| First released | 2024 |
| Minimum Python | 3.10+ |
| Primary use case | Human approval, content guardrails, retries, and structured output. |

AgentMiddleware lets you add cross-cutting behavior (retry, fallbacks, guardrails, human-in-the-loop) without modifying the agent itself. Stack middlewares — order matters.
