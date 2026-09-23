# Deployment

LangGraph apps can be deployed on the LangGraph Platform:

1. Add a langgraph.json at the project root pointing to your compiled graph.
2. Define dependencies in pyproject.toml or requirements.txt.
3. Deploy via the LangSmith UI (Deployments → New) or the langgraph CLI.

Platform features:
- Built-in persistence (Postgres-backed checkpointer)
- Streaming over WebSockets
- Background runs and crons
- Auth hooks for per-tenant access

For self-hosting, the same image can be run via docker compose — see the
self-hosted LangSmith docs for a worked example.
