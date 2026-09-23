# Agent code standards

## Use the framework's constructs

- **Build agents with the framework's agent constructor or graph API.** Do not
  hand-roll a tool-calling loop. Hand-rolled loops lose retries, streaming,
  checkpointing and tracing, and they are re-discovered as bugs one at a time.
- **Use structured output whenever downstream code parses the result.** Parsing
  prose is a defect waiting for a model update.
- **Return new state from a node; never mutate the state object in place.** The
  framework's reducer merges returned values. In-place mutation appears to work
  and then loses updates under concurrency.

## Context

- **Do not put whole documents in the system prompt.** Retrieve instead. A
  prompt that grows with the corpus gets slower, more expensive and less
  accurate at the same time.
- **Keep the always-on prompt short.** Anything conditional belongs in a skill
  loaded on demand, not in every request.

## Review

- Two approvals for any change to a prompt, a tool's behaviour, or the
  middleware chain. One approval is enough for tests, comments and docs.
- The reviewer reads a trace from the change, not only the diff. A prompt diff
  tells you almost nothing about what the agent will now do.
