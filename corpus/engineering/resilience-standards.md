# Resilience standards

Providers rate-limit, time out, and fail. An agent that assumes otherwise fails
in production at the worst moment.

## Required

- **Retry middleware on every model call.** Providers return 429s under normal
  operation; a run without retries treats routine back-pressure as an outage.
- **Checkpointing for any agent that can be interrupted** — anything
  long-running, anything with human-in-the-loop, anything a user can close a
  browser tab on. Without it an interruption means starting over.
- **A timeout on every external tool call.** A tool with no timeout converts a
  slow upstream into a hung agent, which is harder to diagnose than an error.

## Forbidden

- **Calling a model in a tight loop without retries.** Provider 429s will crash
  the run, and the crash will happen in production rather than in `staging`.
- **Synchronous calls inside an async path.** It blocks the event loop and
  destroys concurrency for every other caller on that worker — the symptom is
  everyone's latency, not yours.
- **`max_tokens` set below the length the answer needs.** Answers truncate
  mid-sentence, and truncation reads to a user as the agent being wrong rather
  than as a configuration error.
