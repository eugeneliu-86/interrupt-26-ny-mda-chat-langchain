# Tracing

> Capture every LLM, tool, and chain call automatically.

| | |
|---|---|
| Package | `langsmith` |
| First released | 2023 |
| Minimum Python | 3.9+ |
| Primary use case | Debugging agents, building eval datasets from real traffic. |

Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in your env. Every LangChain/LangGraph run is traced to LangSmith automatically. For arbitrary Python functions use the @traceable decorator.
