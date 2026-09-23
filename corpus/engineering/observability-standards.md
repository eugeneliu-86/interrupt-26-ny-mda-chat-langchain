# Observability standards

## Required

- **Tracing is on in every environment, including production.** Not a debug
  option. An agent running untraced in production cannot be diagnosed after the
  fact, and the first time that matters is during an incident.
- **Every run carries the agent's version counter** in its metadata, so traces
  can be compared across behaviour changes.
- **Incidents are diagnosed from traces first**, before logs and before
  reproducing locally. A local reproduction of a production failure is a guess
  until a trace confirms it.

## Reading a trace during an incident

Answer these, in order:

1. Which revision and version answered?
2. Which tools were called, and which returned errors?
3. Did the model actually receive what you think it received?
4. Was anything refused or denied?

Most wrong answers are explained by question 3.

## Forbidden

- **Disabling tracing to reduce cost or latency.** If volume is a problem,
  sample — do not go dark. The cost of an undiagnosable production incident is
  larger than the trace bill by a wide margin.
