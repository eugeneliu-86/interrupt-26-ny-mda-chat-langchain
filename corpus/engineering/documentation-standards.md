# Documentation standards

## Linking

- The canonical documentation domain is **`docs.langchain.com`**. Link there.
- `python.langchain.com` and `js.langchain.com` are **stale**. Do not link them,
  and replace them when you find them in our code, prompts or tickets. An agent
  that cites a stale domain teaches every one of its users the wrong URL.

## Writing runbooks

A runbook page is for someone under time pressure who did not write it.

- Procedural and ordered. Steps, commands, names.
- State the order that matters and why, when the order is surprising — see the
  rollback-before-diagnose rule in `break-glass.md`.
- Name the specific thing: the pipeline, the ticket prefix, the channel, the
  environment. A runbook that says "notify the team" has not said anything.
- One page, one procedure. If a page needs a table of contents, split it.
- Say what NOT to do when it is tempting and wrong, and say what goes wrong.

## Keeping them true

- A runbook that was wrong during an incident is a `PLAT-` ticket, filed from
  the incident review.
- Reviewed every six months. An unreviewed runbook is worse than none: it is
  trusted and wrong.
