# The eval gate

No prompt or agent-code change reaches production without passing its agent's
eval gate. Product documentation covers how evaluation works; this page is the
rule we apply.

## The gate

Every agent has a versioned regression dataset named `plat-<agent>-regression`.
`agent-checks` runs it on every pull request that touches the agent's prompt,
tools, middleware or model.

The change may merge when:

- no case that previously passed now fails, and
- the overall score has not dropped, and
- any new behaviour has at least one case covering it.

A change that improves one case and breaks another is **not** a pass. Fix or
explicitly retire the broken case, with the reason on the `PLAT-` ticket.

## Adding cases

- Every production incident that produced a wrong answer becomes a case. This
  is not optional, and it is the main reason the dataset is worth anything.
- Cases assert what the agent *did* — which tools it called, what it cited —
  not the exact prose. A test pinned to wording fails on an unrelated model
  change and gets deleted rather than fixed.

## Retiring cases

Only with a reason on the ticket and a second engineer's agreement. A dataset
that quietly loses its hard cases will report a passing gate forever.
